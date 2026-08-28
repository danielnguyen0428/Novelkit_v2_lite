"""Shared PipelineState persistence boundary for the unified control plane."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # POSIX advisory locking (darwin/linux). Windows falls back to no-op.
    import fcntl

    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX
    _HAVE_FCNTL = False

from tools.novelkit_pipeline_tool import (
    PIPELINE_SCHEMA_VERSION,
    PIPELINE_STATUS_REL_PATH,
    PipelineEngine,
    PipelineState,
    migrate_state,
)

PIPELINE_STATE_REL_PATH = "logs/pipeline_state.json"
CHECKPOINTS_REL_PATH = "logs/checkpoints.jsonl"

CHECKPOINT_STEPS = {
    "plan_started",
    "plan_completed",
    "draft_started",
    "draft_completed",
    "self_check_completed",
    "review_completed",
    "rewrite_queued",
    "polish_queued",
    "sync_started",
    "canon_promoted",
    "commit_ledger_written",
    "derivatives_updated",
    "sync_completed",
    # Long-form GA (Req 12.1)
    "compass_updated",
    "arc_expanded",
    "volume_expanded",
    "arc_summary_written",
    "volume_summary_written",
    "steer_applied",
    # Knowledge graph (Req 7): derivative KG rebuilt at sync time.
    "graph_updated",
}


class PipelineStateConflict(RuntimeError):
    """Raised when a caller tries to save over a newer PipelineState revision."""


class PipelineStateDigestError(RuntimeError):
    """Raised when a persisted PipelineState digest does not match its payload."""


def _fsync_dir(directory: Path) -> None:
    """fsync a directory so a rename into it survives a crash (POSIX only)."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:  # pragma: no cover - platform without dir fds (e.g. Windows)
        return
    try:
        os.fsync(fd)
    except OSError:  # pragma: no cover - some filesystems reject dir fsync
        pass
    finally:
        os.close(fd)


def atomic_write_json(path: Path, payload: Any) -> None:
    """Atomically write JSON via sibling temp file + fsync + os.replace.

    The temp file is created with :func:`tempfile.mkstemp` in the target
    directory so its name is unique per call — two threads in the same process
    (which share a pid) no longer collide on a ``<name>.<pid>.tmp`` sibling. The
    parent directory is fsynced after the rename so the new directory entry is
    durable across a crash, not just the file contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f"{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    finally:
        with contextlib.suppress(OSError):
            if tmp.exists():
                tmp.unlink()


class PipelineStateStore:
    """File-first authority boundary for one novel's durable PipelineState."""

    def __init__(
        self,
        novel_path: str | Path,
        *,
        state_path: str | Path | None = None,
        status_path: str | Path | None = None,
    ):
        self.novel_path = Path(novel_path)
        self._state_path = Path(state_path) if state_path is not None else None
        self._status_path = Path(status_path) if status_path is not None else None

    @classmethod
    def from_state_path(cls, state_path: str | Path) -> "PipelineStateStore":
        path = Path(state_path)
        if path.name == "pipeline_state.json" and path.parent.name == "logs":
            return cls(path.parent.parent)
        return cls(
            path.parent,
            state_path=path,
            status_path=path.with_name("pipeline_status.json"),
        )

    @property
    def state_path(self) -> Path:
        if self._state_path is not None:
            return self._state_path
        return self.novel_path / PIPELINE_STATE_REL_PATH

    @property
    def status_path(self) -> Path:
        if self._status_path is not None:
            return self._status_path
        return self.novel_path / PIPELINE_STATUS_REL_PATH

    @property
    def checkpoints_path(self) -> Path:
        return self.novel_path / CHECKPOINTS_REL_PATH

    @property
    def _lock_path(self) -> Path:
        """Sibling lock file guarding writes to this novel's state + checkpoints."""
        return self.state_path.with_name(self.state_path.name + ".lock")

    @contextlib.contextmanager
    def _locked(self):
        """Hold an exclusive advisory lock for the duration of a write.

        Closes the check-then-act (TOCTOU) window in :meth:`save` and serialises
        the read-modify-append in :meth:`append_checkpoint` so a concurrent
        writer cannot clobber a newer revision or reuse a checkpoint ``seq``. A
        no-op on platforms without ``fcntl`` (single-writer assumption there).
        """
        if not _HAVE_FCNTL:
            yield
            return
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    @staticmethod
    def _validate_digest(payload: dict[str, Any]) -> None:
        recorded = payload.get("state_digest")
        if not recorded:
            return
        expected = PipelineState.from_dict(payload).to_dict()["state_digest"]
        if recorded != expected:
            raise PipelineStateDigestError(
                f"state_digest mismatch: expected {expected}, found {recorded}"
            )

    def load_payload(self) -> dict[str, Any]:
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self._validate_digest(payload)
        # Auto-upgrade older-schema payloads on load — validate the ORIGINAL
        # digest first (above), then migrate so the returned payload carries the
        # current schema + a freshly-computed digest (lossless + idempotent, P24).
        if int(payload.get("schema_version", 0)) != PIPELINE_SCHEMA_VERSION:
            payload = migrate_state(payload)
        return payload

    def load_state(self) -> PipelineState:
        return PipelineState.from_dict(self.load_payload())

    def save(
        self,
        state: PipelineState | dict[str, Any],
        *,
        expected_version: int | None = None,
        write_status: bool = True,
    ) -> dict[str, Any]:
        payload = (
            state.to_dict()
            if isinstance(state, PipelineState)
            else PipelineState.from_dict(state).to_dict()
        )
        # The version check and the write must be one critical section: reading
        # the current version, comparing it, then writing is a check-then-act
        # (TOCTOU) that two writers could both pass. The lock serialises them so
        # the optimistic-version guard is actually atomic.
        with self._locked():
            if expected_version is not None and self.state_path.exists():
                current = self.load_payload()
                if current.get("state_version") != expected_version:
                    raise PipelineStateConflict(
                        f"expected state_version {expected_version}, "
                        f"found {current.get('state_version')}"
                    )
            atomic_write_json(self.state_path, payload)
        if write_status:
            self.write_status_projection(payload)
        return payload

    def write_status_projection(self, state: PipelineState | dict[str, Any]) -> dict[str, Any]:
        payload = (
            state.to_dict()
            if isinstance(state, PipelineState)
            else PipelineState.from_dict(state).to_dict()
        )
        status = PipelineEngine(PipelineState.from_dict(payload)).status_snapshot()
        atomic_write_json(self.status_path, status)
        return status

    def _next_checkpoint_seq(self) -> int:
        if not self.checkpoints_path.exists():
            return 1
        seq = 0
        for line in self.checkpoints_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            seq = max(seq, int(payload.get("seq") or 0))
        return seq + 1

    def _artifact_record(self, rel_path: str) -> dict[str, Any]:
        root = self.novel_path.resolve()
        path = (self.novel_path / rel_path).resolve()
        # Path-traversal guard (do NOT remove): resolve() collapses ``..`` and
        # symlinks, then relative_to() raises ValueError if the artifact escaped
        # the novel root. This blocks a malicious rel_path like "../../etc/passwd".
        if not path.is_relative_to(root):
            raise ValueError(f"artifact path escapes novel root: {rel_path!r}")
        data = path.read_bytes()
        return {
            "path": rel_path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }

    def append_checkpoint(
        self,
        *,
        task_key: str,
        step: str,
        state: PipelineState | dict[str, Any],
        input_digest: str,
        artifacts: list[str] | None = None,
        commit_id: str | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        if step not in CHECKPOINT_STEPS:
            raise ValueError(f"unknown checkpoint step {step!r}")
        payload = (
            state.to_dict()
            if isinstance(state, PipelineState)
            else PipelineState.from_dict(state).to_dict()
        )
        # Serialise the seq read-modify-append: two concurrent callers must not
        # compute the same seq and produce duplicate checkpoint sequence numbers.
        with self._locked():
            checkpoint = {
                "schema_version": 1,
                "seq": self._next_checkpoint_seq(),
                "novel_id": payload.get("novel") or self.novel_path.name,
                "scope": scope or task_key,
                "task_key": task_key,
                "step": step,
                "input_digest": input_digest,
                "artifacts": [
                    self._artifact_record(rel_path) for rel_path in (artifacts or [])
                ],
                "commit_id": commit_id,
                "state_version": payload.get("state_version"),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
            self.checkpoints_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoints_path, "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(checkpoint, ensure_ascii=False, sort_keys=True) + "\n"
                )
        return checkpoint
