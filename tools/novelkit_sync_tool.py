"""NovelKit sync / memory-commit tool + doctor health-check.

Phase 3 of the migration (Task 10). This Custom Tool **extracts and consolidates**
three legacy modules plus the doctor health-check, and re-packages them as a
single self-registering Hermes tool:

- ``sync_stages.py``    — the 3-stage sync split (ledger / indexes / audit) and
                          its blocking policy.
- ``chapter_commit.py`` — the commit lifecycle (build / accept / load), minus
                          the legacy SQLite control plane. Durable state is a
                          content-addressed JSON commit at
                          ``.commits/chapter_NNNN.commit.json``.
- ``chapter_diff.py``   — chapter version diffing, used to detect whether a
                          sync actually changes canon (idempotency, P11).
- doctor in ``validators.py`` — canon / index / memory coherence, blocked
                          tasks, and artifact provenance checks, re-pointed at
                          the Hermes-native architecture (file-first canon +
                          memory-provider store + pipeline_status snapshot).

Headline interfaces (design.md §"Components and Interfaces" #10)::

    commit(novel_path, chapter) -> SyncReport
        review gate → update PLAN/GOAL_TRACKER/Memory → reindex (context-engine)
        → episodic commit (memory-provider) → doctor → provenance → rolling seed.

    health_check(novel_path) -> list[Issue]    # the doctor

Semantics preserved
--------------------
- **Review gate** (Requirement 11.1): the sync gate reuses the canonical
  ``review_gate_passes`` rule from the pipeline tool — hard_fail/soft_fail
  block, explicit pass allows, ``None`` allows only when ``score ≥
  REVIEW_PASS_SCORE`` (85). The score + verdict are parsed by the gate tool so
  the gate and sync never diverge.
- **3-stage sync** (ported from ``sync_stages.py``): Stage 1 ``commit_ledger``
  is blocking (durable memory evidence); Stage 2 ``commit_indexes`` and Stage 3
  ``commit_audit`` are non-blocking. Only a Stage-1 failure blocks the next
  chapter.
- **Idempotent commit** (Property P11): the commit is content-addressed by the
  chapter + review SHA-256s; running sync twice on the same state re-uses the
  existing commit and rewrites the planning docs to byte-identical content, so
  no canon changes — only derivative state refreshes.
- **Canon authority through sync** (Property P5): the reindex step only rebuilds
  derivative index state (``.rag/`` is a derivative path) and never writes to a
  canon file; the rebuilt context engine still ranks canon above derivative.
- **Rotation** (Requirement 11.3): when active memory exceeds
  MEMORY_ACTIVE_MAX_WORDS (3500) the memory provider rotates resolved state to
  archive.
- **Style Coherence Audit** (Requirement 11.4): runs every ``N % 10 == 0``.
- **Provenance** (Requirement 11.5): every output artifact is fingerprinted
  (SHA-256) and recorded on the commit for traceability.

Design references: design.md §"Components and Interfaces" #10, §"Correctness
Properties" P5 & P11, §"Error Handling" (blocking vs report-only doctor).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from tools import registry

# Reuse the canonical review gate + thresholds (never re-declare divergent rules).
from tools.novelkit_pipeline_tool import (
    REVIEW_PASS_SCORE,
    PipelineEngine,
    PipelineState,
    review_gate_passes,
)
from tools.novelkit_gate_tool import parse_review_file
from tools.novelkit_rules_tool import current_rules_digest

# Style audit cadence (Requirement 11.4) is owned by the style-coherence tool.
from tools.novelkit_style_coherence_tool import audit as _style_audit
from tools.novelkit_style_coherence_tool import style_audit_due

# Memory provider (episodic commit + rotation) and its rotation threshold.
from plugins.memory.novelkit_memory import (
    MEMORY_ACTIVE_MAX_WORDS,
    get_provider,
)

# Context engine (reindex + canon authority, P5).
from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    Chunk,
    authority_rank_for_path,
    build_engine,
    is_canon_path,
)


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Relative path of the content-addressed commit ledger (replaces SQLite, D2).
COMMITS_REL_DIR = ".commits"

#: Derivative retrieval index metadata (a derivative path — never canon, P5).
RAG_INDEX_META_REL_PATH = ".rag/index_meta.json"

#: Canon / planning text files whose content sync must keep idempotent (P11).
#: (Globs are evaluated relative to the novel directory.)
_CANON_TEXT_GLOBS: tuple[str, ...] = (
    "PROJECT_DNA.md",
    "PLAN.md",
    "GOAL_TRACKER.md",
    "memory/Memory.md",
    "chapters/*.md",
    "reviews/*.md",
    "outlines/**/*.md",
    "database/**/*.md",
)

CHAPTER_RE = re.compile(r"(?:chapter_|ch)(\d+)", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Sync stages (ported from sync_stages.py)
# --------------------------------------------------------------------------- #


class SyncStageKind(str, Enum):
    """Identifies which sync operation a stage performs."""

    COMMIT_LEDGER = "commit_ledger"
    COMMIT_INDEXES = "commit_indexes"
    COMMIT_AUDIT = "commit_audit"


class BlockingPolicy(str, Enum):
    """Whether a stage failure blocks the next chapter from starting."""

    BLOCKING = "blocking"
    NON_BLOCKING = "non_blocking"


@dataclass(frozen=True)
class SyncStageSpec:
    """Specification for a single sync stage (ported)."""

    kind: SyncStageKind
    order: int
    blocking: BlockingPolicy


#: The canonical ordered list of sync stages. Only Stage 1 blocks.
SYNC_STAGES: tuple[SyncStageSpec, ...] = (
    SyncStageSpec(SyncStageKind.COMMIT_LEDGER, 1, BlockingPolicy.BLOCKING),
    SyncStageSpec(SyncStageKind.COMMIT_INDEXES, 2, BlockingPolicy.NON_BLOCKING),
    SyncStageSpec(SyncStageKind.COMMIT_AUDIT, 3, BlockingPolicy.NON_BLOCKING),
)


@dataclass
class SyncStageResult:
    """Result of executing a single sync stage."""

    stage: str
    success: bool
    blocking: bool
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Doctor issue model (compatible with the legacy ValidationIssue shape)
# --------------------------------------------------------------------------- #


@dataclass
class Issue:
    """A single doctor finding (canon/index/memory coherence, provenance)."""

    code: str
    severity: str  # "error" (hard-block) · "warning" · "info"
    message: str
    path: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Doctor codes that block the autonomous pipeline regardless of severity
#: (ported from validators.blocking_issues_for_autonomous, re-pointed at the
#: Hermes-native architecture). Any ``error`` severity also blocks.
_BLOCKING_CODES = frozenset(
    {
        "missing_path",
        "invalid_pipeline_status",
        "blocked_tasks_present",
        "breaker_open",
        "canon_index_incoherent",
        "rag_index_stale",
        "commit_provenance_missing",
    }
)


def classify_blocking(issues: list[Issue]) -> list[Issue]:
    """Filter the doctor issues that truly block the autonomous pipeline.

    Policy (ported): an ``error`` severity issue blocks, as does any issue whose
    code is in :data:`_BLOCKING_CODES`. Warnings/info are report-only.
    """
    return [
        issue
        for issue in issues
        if issue.severity == "error" or issue.code in _BLOCKING_CODES
    ]


# --------------------------------------------------------------------------- #
# Chapter commit (ported from chapter_commit.py, SQLite control plane dropped)
# --------------------------------------------------------------------------- #


class ReviewGateFailed(Exception):
    """Raised when the review gate has not passed for a chapter."""

    def __init__(self, chapter: int, score: Optional[float], outcome: Optional[str]):
        self.chapter = chapter
        self.score = score
        self.outcome = outcome
        super().__init__(
            f"Review gate failed for chapter {chapter}: "
            f"score={score}, outcome={outcome}"
        )


@dataclass(frozen=True)
class ChapterCommit:
    """Frozen record representing an accepted chapter commit (content-addressed)."""

    commit_id: str
    novel: str
    chapter: int
    arc: Optional[int]
    review_score: Optional[float]
    review_outcome: Optional[str]
    chapter_sha256: str
    review_sha256: str
    summary_text: str
    provenance: dict[str, str] = field(default_factory=dict)
    source_path: str = ""
    review_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChapterCommit":
        return cls(
            commit_id=data["commit_id"],
            novel=data["novel"],
            chapter=int(data["chapter"]),
            arc=data.get("arc"),
            review_score=data.get("review_score"),
            review_outcome=data.get("review_outcome"),
            chapter_sha256=data["chapter_sha256"],
            review_sha256=data["review_sha256"],
            summary_text=data.get("summary_text", ""),
            provenance=dict(data.get("provenance") or {}),
            source_path=data.get("source_path", ""),
            review_path=data.get("review_path", ""),
        )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _extract_summary_text(chapter_text: str) -> str:
    """First paragraph (≤500 chars) of the chapter (ported)."""
    paragraphs = chapter_text.strip().split("\n\n")
    if paragraphs and paragraphs[0].strip():
        return paragraphs[0].strip()[:500]
    return chapter_text.strip()[:500]


def _chapter_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "chapters" / f"chapter_{chapter:03d}.md"


def _draft_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "drafts" / f"chapter_{chapter:04d}.md"


def _self_check_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "drafts" / f"chapter_{chapter:04d}.check.json"


def _typed_review_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "reviews" / f"chapter_{chapter:04d}_review.json"


def _review_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "reviews" / f"chapter_{chapter:03d}_review.md"


def _review_markdown_file(novel_path: Path, chapter: int) -> Path:
    return novel_path / "reviews" / f"chapter_{chapter:04d}_review.md"


def _commit_path(novel_path: Path, chapter: int) -> Path:
    return novel_path / COMMITS_REL_DIR / f"chapter_{chapter:04d}.commit.json"


def _transaction_manifest_path(novel_path: Path, chapter: int, attempt: int) -> Path:
    scope = f"chapter_{chapter:04d}_attempt_{attempt:02d}"
    return novel_path / "logs" / "transactions" / scope / "manifest.json"


def _sync_source_file(novel_path: Path, chapter: int) -> Path:
    draft = _draft_file(novel_path, chapter)
    if draft.exists():
        return draft
    return _chapter_file(novel_path, chapter)


def _relative(novel_path: Path, path: Path) -> str:
    return path.relative_to(novel_path).as_posix()


def _load_typed_review(
    novel_path: Path,
    chapter: int,
    *,
    source_file: Path,
) -> tuple[float, str, int, Path, bool]:
    review_file = _typed_review_file(novel_path, chapter)
    data = json.loads(review_file.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("typed review schema_version must be 2")
    if int(data.get("chapter", -1)) != chapter:
        raise ValueError("typed review chapter does not match sync chapter")
    attempt = int(data.get("attempt", 1) or 1)
    draft_hash = data.get("draft_sha256")
    source_hash = _sha256_file(source_file)
    if draft_hash != source_hash:
        raise ValueError("typed review draft_sha256 does not match source draft")
    review_rules_digest = data.get("rules_digest")
    active_rules_digest = current_rules_digest(novel_path)
    if review_rules_digest != active_rules_digest:
        raise ValueError("typed review rules_digest does not match current rules")
    outcome = str(data.get("gate_outcome") or "")
    final_action = str(data.get("final_action") or "")
    score = float(data.get("overall_score"))
    # Human approval override: an operator can manually pass a chapter the AI
    # could not lift above the quality bar (the "Duyệt tay" valve). The draft +
    # rules validation above still runs, so approval only applies to the exact
    # reviewed draft under the current rules — a stale approval never sneaks a
    # changed draft through. When approved we accept regardless of gate_outcome.
    if bool(data.get("human_approved")):
        return score, "pass", attempt, review_file, True
    if outcome != "pass" or final_action != "sync":
        raise ReviewGateFailed(chapter, score, outcome or final_action)
    return score, outcome, attempt, review_file, False


def stamp_human_approval(
    novel_path: Path, chapter: int, *, approver: Optional[str] = None
) -> dict[str, Any]:
    """Make the SYNC gate accept ``chapter`` on the operator's authority.

    The "Duyệt tay" valve needs a typed review JSON carrying ``human_approved``
    so :func:`_load_typed_review` lets sync through. Two cases:

    - **Review JSON exists** (chapter blocked at review/sync): stamp the flag
      onto it in place.
    - **Review JSON absent** (chapter blocked at self_check, before review ran):
      synthesise a minimal, VALID typed review for the current draft — correct
      ``draft_sha256`` + ``rules_digest`` so the sync validation still binds the
      approval to this exact draft under the current rules — and mark it
      approved. This is what lets approval work when the block is *earlier* than
      review, which is exactly the self_check repeated-sentence case.

    Returns ``{"created": bool, "stamped": bool}``. Best-effort by design: if
    there is no draft to hash, nothing is written.
    """
    from datetime import datetime, timezone

    review_file = _typed_review_file(novel_path, chapter)
    source_file = _sync_source_file(novel_path, chapter)

    if review_file.exists():
        try:
            data = json.loads(review_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        if not source_file.exists():
            return {"created": False, "stamped": False}
        from tools.novelkit_gate_tool import derive_typed_review

        draft_sha = _sha256_file(source_file)
        # Score at the pass bar: the gate check is overridden by human_approved
        # anyway, but a valid, self-consistent review keeps downstream readers
        # (diagnostics, projections) sane.
        dims = {
            "plot_progression": REVIEW_PASS_SCORE,
            "character_consistency": REVIEW_PASS_SCORE,
            "continuity": REVIEW_PASS_SCORE,
            "prose_quality": REVIEW_PASS_SCORE,
            "dialogue_voice": REVIEW_PASS_SCORE,
            "world_consistency": REVIEW_PASS_SCORE,
            "reader_momentum": REVIEW_PASS_SCORE,
        }
        data = derive_typed_review(
            review_id=f"chapter_{chapter:04d}_human_approved",
            chapter=chapter,
            attempt=1,
            draft_sha256=draft_sha,
            dimensions=dims,
            rules_digest=current_rules_digest(novel_path),
            reviewer_model_fingerprint="human:approval",
        )

    created = not review_file.exists()
    data["human_approved"] = True
    data["human_approved_at"] = datetime.now(timezone.utc).isoformat()
    if approver:
        data["human_approved_by"] = approver
    review_file.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(review_file, data)
    return {"created": created, "stamped": True}


def _legacy_review_source(novel_path: Path, chapter: int) -> Path:
    legacy = _review_file(novel_path, chapter)
    if legacy.exists():
        return legacy
    return _review_markdown_file(novel_path, chapter)


def _initial_manifest(
    novel_path: Path,
    built: ChapterCommit,
    *,
    attempt: int,
    source_file: Path,
    review_file: Path,
) -> dict[str, Any]:
    canon_file = _chapter_file(novel_path, built.chapter)
    pre_write_hashes: dict[str, Optional[str]] = {}
    for rel in (
        _relative(novel_path, canon_file),
        "PLAN.md",
        "GOAL_TRACKER.md",
        "memory/Memory.md",
    ):
        path = novel_path / rel
        pre_write_hashes[rel] = _sha256_file(path) if path.exists() else None
    return {
        "schema_version": 1,
        "chapter": built.chapter,
        "attempt": attempt,
        "scope": f"chapter_{built.chapter:04d}_attempt_{attempt:02d}",
        "source_draft": {
            "path": _relative(novel_path, source_file),
            "sha256": built.chapter_sha256,
        },
        "review": {
            "path": _relative(novel_path, review_file),
            "sha256": built.review_sha256,
        },
        "expected_canon_path": _relative(novel_path, canon_file),
        "expected_pre_write_hashes": pre_write_hashes,
        "staged_output_hashes": {},
        "commit_id": built.commit_id,
        "completed_substeps": [],
        "status": "running",
    }


def build_commit(
    novel_path: Path, chapter: int, arc: Optional[int] = None
) -> ChapterCommit:
    """Build a :class:`ChapterCommit`, enforcing the review gate (Requirement 11.1).

    Pure given filesystem reads: parses the review for (score, outcome) via the
    gate tool's parser and applies :func:`review_gate_passes`. Raises
    :class:`ReviewGateFailed` when the gate blocks, :class:`FileNotFoundError`
    when the chapter/review is missing.
    """
    source_file = _sync_source_file(novel_path, chapter)
    chapter_text = source_file.read_text(encoding="utf-8")
    typed_review = _typed_review_file(novel_path, chapter)
    human_approved = False
    if typed_review.exists():
        score, outcome, _attempt, review_file, human_approved = _load_typed_review(
            novel_path,
            chapter,
            source_file=source_file,
        )
    else:
        if source_file == _draft_file(novel_path, chapter):
            raise FileNotFoundError(
                f"typed review JSON required for draft sync: "
                f"{_relative(novel_path, typed_review)}"
            )
        review_file = _legacy_review_source(novel_path, chapter)
        review_file.read_text(encoding="utf-8")  # ensure readable
        parsed = parse_review_file(review_file)
        score, outcome = parsed.score, parsed.verdict
        if not review_gate_passes(score, outcome):
            raise ReviewGateFailed(chapter, score, outcome)

    if not human_approved:
        from tools.novelkit_language_guard_tool import (
            blocking_violations,
            scan,
            workspace_guard_context,
        )

        primary, secondary, allow_modern = workspace_guard_context(novel_path)
        violations = scan(
            chapter_text,
            primary,
            secondary,
            allow_modern_register=allow_modern,
        )
        blocked = blocking_violations(
            violations,
            primary,
            allow_modern_register=allow_modern,
        )
        if blocked:
            blocked_score = min(score, 69.0) if score is not None else 69.0
            raise ReviewGateFailed(chapter, blocked_score, "language_guard")

    return ChapterCommit(
        commit_id=str(uuid.uuid4()),
        novel=novel_path.name,
        chapter=chapter,
        arc=arc,
        review_score=score,
        review_outcome=outcome,
        chapter_sha256=_sha256_file(source_file),
        review_sha256=_sha256_file(review_file),
        summary_text=_extract_summary_text(chapter_text),
        provenance={},
        source_path=_relative(novel_path, source_file),
        review_path=_relative(novel_path, review_file),
    )


def load_commit(novel_path: Path, chapter: int) -> Optional[ChapterCommit]:
    """Load the persisted commit for ``chapter`` (None when absent/unreadable)."""
    path = _commit_path(novel_path, chapter)
    if not path.exists():
        return None
    try:
        return ChapterCommit.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, KeyError):
        return None


def accept_commit(
    novel_path: Path, commit: ChapterCommit
) -> tuple[ChapterCommit, bool]:
    """Persist a commit idempotently. Returns ``(commit, created)``.

    Content-addressed: if a stored commit with identical chapter+review SHA-256s
    already exists, it is returned unchanged (``created=False``) — this is what
    makes a repeated sync a no-op on canon (P11). A stored commit with different
    fingerprints (a genuine rewrite) is overwritten in place.
    """
    existing = load_commit(novel_path, commit.chapter)
    if (
        existing is not None
        and existing.chapter_sha256 == commit.chapter_sha256
        and existing.review_sha256 == commit.review_sha256
    ):
        return existing, False

    path = _commit_path(novel_path, commit.chapter)
    _atomic_write_json(path, commit.to_dict())
    return commit, True


# --------------------------------------------------------------------------- #
# Planning-doc updates (idempotent, marker-keyed) — PLAN / GOAL_TRACKER / Memory
# --------------------------------------------------------------------------- #


def _upsert_marked_block(
    path: Path,
    *,
    section_header: str,
    marker: str,
    block_text: str,
) -> bool:
    """Insert or replace a marker-keyed block under ``section_header``.

    The block is wrapped between ``<!-- marker -->`` / ``<!-- /marker -->`` HTML
    comments so a repeated sync rewrites it to identical content (idempotent,
    P11) instead of appending a duplicate. Returns True when the file content
    changed.
    """
    open_tag = f"<!-- {marker} -->"
    close_tag = f"<!-- /{marker} -->"
    wrapped = f"{open_tag}\n{block_text.rstrip()}\n{close_tag}"

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    text = original

    block_re = re.compile(
        re.escape(open_tag) + r".*?" + re.escape(close_tag),
        re.DOTALL,
    )
    if block_re.search(text):
        text = block_re.sub(wrapped, text)
    else:
        if section_header and section_header not in text:
            text = text.rstrip()
            if text:
                text += "\n\n"
            text += f"{section_header}\n"
        text = text.rstrip() + "\n\n" + wrapped + "\n"

    if text == original:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def update_planning_docs(novel_path: Path, commit: ChapterCommit) -> list[str]:
    """Upsert the chapter's sync state into PLAN / GOAL_TRACKER / Memory.

    Each document gets one chapter-keyed block; re-running the sync replaces the
    block with identical content, so the docs are stable across repeated syncs
    (P11). Returns the relative paths that actually changed.
    """
    ch = commit.chapter
    marker = f"sync:chapter-{ch:04d}"
    changed: list[str] = []

    plan_block = (
        f"- Chapter {ch}: synced "
        f"(score={commit.review_score}, outcome={commit.review_outcome})"
    )
    if _upsert_marked_block(
        novel_path / "PLAN.md",
        section_header="## Sync Log",
        marker=marker,
        block_text=plan_block,
    ):
        changed.append("PLAN.md")

    goal_block = f"- Chapter {ch}: accepted into canon."
    if _upsert_marked_block(
        novel_path / "GOAL_TRACKER.md",
        section_header="## Progress",
        marker=marker,
        block_text=goal_block,
    ):
        changed.append("GOAL_TRACKER.md")

    memory_block = f"### Chapter {ch}\n{commit.summary_text}"
    if _upsert_marked_block(
        novel_path / "memory" / "Memory.md",
        section_header="## Chapter Memory",
        marker=marker,
        block_text=memory_block,
    ):
        changed.append("memory/Memory.md")

    return changed


# --------------------------------------------------------------------------- #
# Reindex (context-engine) — derivative only, never writes canon (P5)
# --------------------------------------------------------------------------- #


def _iter_canon_files(novel_path: Path) -> list[Path]:
    """Collect the file-first canon files to (re)index (derivative state)."""
    files: list[Path] = []
    seen: set[Path] = set()
    for rel in (
        "PROJECT_DNA.md",
        "PROJECT_DNA.rules.json",
        "memory/Memory.md",
    ):
        candidate = novel_path / rel
        if candidate.is_file() and candidate not in seen:
            files.append(candidate)
            seen.add(candidate)
    for pattern in (
        "chapters/*.md",
        "reviews/*.md",
        "reviews/*.json",
        "summaries/**/*.json",
        "summaries/**/*.md",
        "outlines/**/*.md",
        "database/**/*.md",
    ):
        for candidate in sorted(novel_path.glob(pattern)):
            if candidate.is_file() and candidate not in seen:
                files.append(candidate)
                seen.add(candidate)
    return files


def reindex(novel_path: Path) -> dict[str, Any]:
    """Rebuild the derivative retrieval index from canon (Requirement 11.2).

    Builds a context engine over the current canon files and records a
    deterministic ``.rag/index_meta.json`` (file → content fingerprint) so the
    doctor can detect a stale index. This step is *derivative only*: it never
    writes a canon file, preserving canon authority (P5). The meta has no
    timestamps so a repeated reindex on unchanged canon is byte-identical (P11).
    """
    novel_path = Path(novel_path)
    files = _iter_canon_files(novel_path)
    chunks: list[Chunk] = []
    manifest: dict[str, str] = {}
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(novel_path).as_posix()
        manifest[rel] = _sha256_text(text)
        chunks.append(Chunk(path=rel, heading=path.stem, content=text))

    engine = build_engine(chunks)
    canon_chunks = sum(1 for c in chunks if is_canon_path(c.path))

    meta = {
        "schema": 1,
        "total_chunks": len(chunks),
        "canon_chunks": canon_chunks,
        "file_manifest": manifest,
    }
    meta_path = novel_path / RAG_INDEX_META_REL_PATH
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "indexed_chunks": len(chunks),
        "canon_chunks": canon_chunks,
        "derivative_chunks": len(chunks) - canon_chunks,
        "engine_ready": engine is not None,
        "manifest_files": len(manifest),
    }


# --------------------------------------------------------------------------- #
# Episodic commit (memory-provider) — idempotent layer-D write
# --------------------------------------------------------------------------- #


def commit_episodic(novel_path: Path, commit: ChapterCommit) -> dict[str, Any]:
    """Commit the chapter summary as an episodic memory fact (Requirement 11.2).

    Idempotent: the fact's dedupe key is ``story_facts:chapter_NNNN:summary``;
    re-committing the same value is a no-op in the provider, so a repeated sync
    does not mutate memory (P11). Returns the upsert counts.
    """
    provider = get_provider()
    fact = {
        "category": "story_facts",
        "subject": f"chapter_{commit.chapter:04d}",
        "field": "summary",
        "value": commit.summary_text or f"Chapter {commit.chapter} accepted.",
        "confidence": 0.9,
    }
    result = provider.commit_episodic(
        scope=novel_path,
        memory_facts=[fact],
        chapter=commit.chapter,
        commit_id=commit.commit_id,
    )
    return {
        "inserted": result.inserted,
        "updated": result.updated,
        "outdated": result.outdated,
        "contradicted": result.contradicted,
        "tentative_replaced": result.tentative_replaced,
    }


# --------------------------------------------------------------------------- #
# Knowledge-graph rebuild (Req 7) — best-effort, derivative, never blocks sync
# --------------------------------------------------------------------------- #


def _maybe_build_graph(novel_path: Path, chapter: int) -> Optional[dict[str, Any]]:
    """Best-effort KG rebuild after a canon update (Req 7). Never breaks sync.

    Gated behind the ``graph`` feature flag (read from
    ``<novel_path>/config/longform.json``): when the flag is off this is a no-op
    and returns ``None`` (so a flag-off sync is byte-for-byte the legacy flow —
    P11 non-regression). When on, it rebuilds the derivative
    ``logs/knowledge_graph.json`` through ``chapter`` and attaches the *pure*
    contradiction findings. The whole body is wrapped so a failure here (missing
    ``networkx``, unreadable memory, …) can never fail an already-committed sync.
    """
    try:
        from tools.novelkit_longform_config import flag_enabled

        if not flag_enabled("graph", novel_path):
            return None
        from tools.novelkit_graph_tool import build, detect_contradictions

        result = build(novel_path, through_chapter=chapter)
        # Detection is pure/read-only; the enqueue happens on the caller's
        # PipelineState (see commit()), never here.
        result["contradictions"] = detect_contradictions(novel_path)
        return result
    except Exception:  # noqa: BLE001 — derivative; sync already succeeded
        return None


# --------------------------------------------------------------------------- #
# Doctor — health_check(novel_path) -> Issue[]  (ported from validators.py)
# --------------------------------------------------------------------------- #

#: Required planning/canon files the doctor expects after bootstrap (ported,
#: re-pointed at the Hermes-native layout — no legacy control-plane DB).
_REQUIRED_PATHS: tuple[str, ...] = (
    "PROJECT_DNA.md",
    "GOAL_TRACKER.md",
    "PLAN.md",
    "memory/Memory.md",
    "logs/pipeline_status.json",
)


def _synced_chapters(novel_path: Path) -> list[int]:
    """Chapters with a persisted commit, ascending."""
    commits_dir = novel_path / COMMITS_REL_DIR
    if not commits_dir.is_dir():
        return []
    chapters: list[int] = []
    for path in commits_dir.glob("chapter_*.commit.json"):
        match = CHAPTER_RE.search(path.name)
        if match:
            chapters.append(int(match.group(1)))
    return sorted(set(chapters))


def _load_pipeline_status(novel_path: Path) -> Any:
    path = novel_path / "logs" / "pipeline_status.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _check_required_paths(novel_path: Path) -> list[Issue]:
    issues: list[Issue] = []
    for rel in _REQUIRED_PATHS:
        if not (novel_path / rel).exists():
            issues.append(
                Issue(
                    code="missing_path",
                    severity="error",
                    message=f"Missing required path: {rel}",
                    path=rel,
                )
            )
    return issues


def _check_pipeline_status(novel_path: Path) -> list[Issue]:
    issues: list[Issue] = []
    status = _load_pipeline_status(novel_path)
    if status is None:
        return issues  # missing file already reported by _check_required_paths
    if not isinstance(status, dict) or "status" not in status:
        issues.append(
            Issue(
                code="invalid_pipeline_status",
                severity="error",
                message="logs/pipeline_status.json is missing required runtime fields.",
                path="logs/pipeline_status.json",
            )
        )
        return issues
    if status.get("status") == "blocked":
        issues.append(
            Issue(
                code="blocked_tasks_present",
                severity="error",
                message="Pipeline status is 'blocked'; resolve before continuing.",
                path="logs/pipeline_status.json",
                suggestion="Inspect the circuit breaker / blocked task and resume deliberately.",
            )
        )
    breaker = status.get("circuit_breaker")
    if isinstance(breaker, dict):
        if (
            breaker.get("hard_fail_count", 0) >= breaker.get("max_hard_fail", 2)
            or breaker.get("soft_fail_count", 0) >= breaker.get("max_soft_fail", 3)
            or breaker.get("total_attempts", 0) >= breaker.get("max_total", 5)
        ):
            issues.append(
                Issue(
                    code="breaker_open",
                    severity="error",
                    message="Circuit breaker is open in the pipeline status snapshot.",
                    path="logs/pipeline_status.json",
                    suggestion="Reset the scope (rewrite/resume) before further autonomous runs.",
                )
            )
    return issues


def _check_commit_provenance(novel_path: Path) -> list[Issue]:
    """Canon/commit coherence + artifact provenance (ported, re-pointed).

    For each synced chapter: the chapter must still exist and its SHA-256 must
    match the commit fingerprint (otherwise the index/commit is stale vs the
    canon file — canon wins, but flagged blocking so a re-sync runs). The commit
    must carry a non-empty provenance fingerprint map (Requirement 11.5).
    """
    issues: list[Issue] = []
    for chapter in _synced_chapters(novel_path):
        commit = load_commit(novel_path, chapter)
        if commit is None:
            continue
        chapter_file = _chapter_file(novel_path, chapter)
        if not chapter_file.exists():
            issues.append(
                Issue(
                    code="canon_index_incoherent",
                    severity="error",
                    message=(
                        f"Commit exists for chapter {chapter} but its canon "
                        "chapter file is missing."
                    ),
                    path=f"chapters/chapter_{chapter:03d}.md",
                )
            )
            continue
        if _sha256_file(chapter_file) != commit.chapter_sha256:
            issues.append(
                Issue(
                    code="canon_index_incoherent",
                    severity="error",
                    message=(
                        f"Chapter {chapter} changed after commit; the commit "
                        "fingerprint is stale vs the canon file."
                    ),
                    path=f"chapters/chapter_{chapter:03d}.md",
                    suggestion="Re-run sync so derivative state tracks the current canon.",
                )
            )
        if not commit.provenance:
            issues.append(
                Issue(
                    code="commit_provenance_missing",
                    severity="warning",
                    message=f"Chapter {chapter} commit has no artifact provenance fingerprints.",
                    path=str(_commit_path(novel_path, chapter).relative_to(novel_path)),
                    suggestion="Re-run sync to record output artifact fingerprints.",
                )
            )
    return issues


def _check_rag_index(novel_path: Path) -> list[Issue]:
    """Index coherence: the derivative manifest must match current canon."""
    meta_path = novel_path / RAG_INDEX_META_REL_PATH
    if not meta_path.exists():
        return []
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            Issue(
                code="rag_index_stale",
                severity="error",
                message="Retrieval index metadata is unreadable.",
                path=RAG_INDEX_META_REL_PATH,
                suggestion="Re-run sync to rebuild the derivative index.",
            )
        ]
    manifest = meta.get("file_manifest", {})
    if not isinstance(manifest, dict):
        return []
    stale: list[str] = []
    for rel, recorded_hash in manifest.items():
        candidate = novel_path / rel
        if not candidate.exists():
            stale.append(rel)
            continue
        if _sha256_file(candidate) != recorded_hash:
            stale.append(rel)
    if stale:
        return [
            Issue(
                code="rag_index_stale",
                severity="error",
                message=(
                    "Retrieval index is out of sync with canon files: "
                    + ", ".join(sorted(stale)[:5])
                ),
                path=RAG_INDEX_META_REL_PATH,
                suggestion="Re-run sync/reindex so retrieval uses current canon.",
            )
        ]
    return []


def _check_memory_coherence(novel_path: Path) -> list[Issue]:
    """Memory coherence: each synced chapter should have an episodic fact."""
    issues: list[Issue] = []
    chapters = _synced_chapters(novel_path)
    if not chapters:
        return issues
    try:
        provider = get_provider()
        items = provider.search("", scope=novel_path, limit=10_000)
    except Exception:  # noqa: BLE001 — memory store optional / degradable
        return issues
    chapters_with_facts = {
        item.source_chapter for item in items if item.source_chapter is not None
    }
    for chapter in chapters:
        if chapter not in chapters_with_facts:
            issues.append(
                Issue(
                    code="memory_episodic_missing",
                    severity="warning",
                    message=(
                        f"Chapter {chapter} is committed but has no episodic "
                        "memory fact recorded."
                    ),
                    path="memory/items.sqlite3",
                    suggestion="Re-run sync so the chapter's episodic state is committed.",
                )
            )
    return issues


def _check_style_staleness(novel_path: Path) -> list[Issue]:
    """Surface "mòn văn phong" from the latest periodic style audit.

    The style-coherence audit (run at sync cadence) records repeated opening
    lines / stale opening patterns across recent chapters. This reads the most
    recent audit report and raises a report-only warning when repetition was
    flagged, so the staleness signal reaches the Doctor panel. Never blocks.
    """
    issues: list[Issue] = []
    audit_dir = novel_path / "reviews" / "style_coherence"
    if not audit_dir.is_dir():
        return issues
    reports = sorted(audit_dir.glob("chapter_*_style_audit.json"))
    if not reports:
        return issues
    latest = reports[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return issues
    repetition = data.get("repetition") or {}
    flags = repetition.get("flags") or {}
    if not flags:
        return issues
    chapter = data.get("chapter")
    issues.append(
        Issue(
            code="style_staleness",
            severity="warning",
            message=(
                f"Văn phong có dấu hiệu mòn quanh chương {chapter}: "
                f"{', '.join(sorted(flags))}. Câu/cụm mở đầu lặp lại so với các "
                f"chương gần đây."
            ),
            path=str(latest.relative_to(novel_path)),
            suggestion=(
                "Đổi cách mở chương (góc nhìn, nhịp, hành động mở màn) để tránh "
                "lặp mô-típ; tham chiếu Style Vault cho biến thể."
            ),
        )
    )
    return issues


def _check_open_loop_continuity(novel_path: Path) -> list[Issue]:
    """Long-range continuity: plot-thread payoffs that are overdue or orphaned.

    Unlike the per-chapter review (which only sees the current draft), this
    looks across the whole open-loop log at the highest synced chapter and
    flags loops whose ``loop_deadline`` has already passed (a promised payoff
    the story never delivered) and seeds that were planted with no payoff ever
    scheduled. Report-only — it never blocks the pipeline, it surfaces drift
    the chapter gate structurally cannot catch.
    """
    issues: list[Issue] = []
    synced = _synced_chapters(novel_path)
    if not synced:
        return issues
    current = synced[-1]
    try:
        from tools.novelkit_strand_tool import weave
    except Exception:  # noqa: BLE001 — strand tool is optional; never break doctor
        return issues
    try:
        report = weave(novel_path, current)
    except Exception:  # noqa: BLE001 — a malformed loop log must not crash doctor
        return issues

    overdue = [
        e for e in report.get("due_payoffs", [])
        if e.get("loop_deadline") is not None and e["loop_deadline"] < current
    ]
    for loop in overdue:
        label = loop.get("summary") or loop.get("event_id") or "open loop"
        issues.append(
            Issue(
                code="payoff_overdue",
                severity="warning",
                message=(
                    f"Tuyến truyện quá hạn trả: '{label}' đặt ở chương "
                    f"{loop.get('chapter_planted')}, hạn payoff chương "
                    f"{loop.get('loop_deadline')} nhưng đã qua chương {current} "
                    f"chưa được trả."
                ),
                path="database/open_loops.jsonl",
                suggestion=(
                    "Trả payoff trong các chương tới, dời deadline có chủ đích, "
                    "hoặc đóng loop nếu nó đã được giải quyết ngầm."
                ),
            )
        )

    if report.get("debt_overload"):
        issues.append(
            Issue(
                code="open_loop_debt_overload",
                severity="warning",
                message=(
                    f"Quá nhiều tuyến mở chưa trả ({report.get('debt_count')}) — "
                    f"nguy cơ độc giả mất theo dõi và payoff bị loãng."
                ),
                path="database/open_loops.jsonl",
                suggestion="Ưu tiên đóng bớt loop cũ trước khi gieo loop mới.",
            )
        )

    return issues


def _check_summary_coverage(novel_path: Path) -> list[Issue]:
    """Layered-summary coverage (Property P15): every ``done`` arc/volume should
    have exactly one summary artifact. Report-only — surfaces a missing
    ``summaries/arc_<id>.md`` / ``summaries/volume_<id>.md`` so the orchestrator
    can schedule the arc/volume summary before expanding the next part."""
    issues: list[Issue] = []
    try:
        from tools.novelkit_compass_tool import read_arc_map
    except Exception:  # noqa: BLE001 — compass tool optional; never break doctor
        return issues
    arc_map = read_arc_map(novel_path)
    seen_volumes: set[str] = set()
    for arc in arc_map.arcs:
        if arc.status != "done":
            continue
        if not (novel_path / "summaries" / f"arc_{arc.arc_id}.md").exists():
            issues.append(
                Issue(
                    code="summary_missing",
                    severity="warning",
                    message=f"Hồi {arc.arc_id} đã hoàn tất nhưng thiếu tóm tắt Hồi.",
                    path=f"summaries/arc_{arc.arc_id}.md",
                    suggestion="Chạy task arc.<id>.summary trước khi khai triển Hồi kế.",
                )
            )
        vol = arc.volume_id
        if vol and vol not in seen_volumes:
            seen_volumes.add(vol)
            same_vol = [a for a in arc_map.arcs if a.volume_id == vol]
            if same_vol and all(a.status == "done" for a in same_vol):
                if not (novel_path / "summaries" / f"volume_{vol}.md").exists():
                    issues.append(
                        Issue(
                            code="summary_missing",
                            severity="warning",
                            message=f"Cuốn {vol} đã hoàn tất nhưng thiếu tóm tắt Cuốn.",
                            path=f"summaries/volume_{vol}.md",
                            suggestion="Chạy task volume.<id>.summary + update_compass.",
                        )
                    )
    return issues


def _check_canon_system(novel_path: Path) -> list[Issue]:
    """Verify genre canon system (skills/novelkit-canon/) is accessible at runtime.

    The Quality Auditor SOUL.md requires reading genre-specific rubrics from
    ``skills/novelkit-canon/canon/system/<genre>/``. If the canon pack is not
    mounted, reviews lack the genre rubric and produce generic-only scores.
    """
    issues: list[Issue] = []
    canon_base = novel_path.parent / "skills" / "novelkit-canon" / "canon" / "system"
    if not canon_base.parent.exists():
        pkg_canon = Path(__file__).resolve().parent.parent / "skills" / "novelkit-canon" / "canon" / "system"
        if not pkg_canon.exists():
            issues.append(
                Issue(
                    code="canon_system_missing",
                    severity="warning",
                    message=(
                        "Genre canon system (skills/novelkit-canon/) not found. "
                        "Quality Auditor reviews will lack genre-specific rubrics."
                    ),
                    path="skills/novelkit-canon/canon/system/",
                    suggestion=(
                        "Ensure skills/novelkit-canon/ is present in the package root "
                        "or mounted at runtime. Without it, reviews are generic-only."
                    ),
                )
            )
    return issues


def health_check(novel_path: "str | Path") -> list[Issue]:
    """Doctor: canon/index/memory coherence, blocked tasks, provenance.

    Returns every finding (blocking + report-only). Use
    :func:`classify_blocking` to select the issues that actually block the
    autonomous pipeline (design §Error Handling: blocking vs report-only).
    """
    path = Path(novel_path)
    issues: list[Issue] = []
    issues.extend(_check_required_paths(path))
    issues.extend(_check_pipeline_status(path))
    issues.extend(_check_commit_provenance(path))
    issues.extend(_check_rag_index(path))
    issues.extend(_check_memory_coherence(path))
    issues.extend(_check_open_loop_continuity(path))
    issues.extend(_check_style_staleness(path))
    issues.extend(_check_summary_coverage(path))
    issues.extend(_check_canon_system(path))
    return issues


# --------------------------------------------------------------------------- #
# Provenance (Requirement 11.5)
# --------------------------------------------------------------------------- #

#: Output artifacts a chapter sync may touch — fingerprinted for traceability.
_PROVENANCE_PATHS: tuple[str, ...] = (
    "PLAN.md",
    "GOAL_TRACKER.md",
    "memory/Memory.md",
)


def compute_provenance(novel_path: Path, chapter: int) -> dict[str, str]:
    """Fingerprint the chapter's output artifacts (SHA-256) for traceability."""
    provenance: dict[str, str] = {}
    candidates = list(_PROVENANCE_PATHS) + [
        f"chapters/chapter_{chapter:03d}.md",
        f"drafts/chapter_{chapter:04d}.md",
        f"drafts/chapter_{chapter:04d}.check.json",
        f"reviews/chapter_{chapter:04d}_review.json",
        f"reviews/chapter_{chapter:04d}_review.md",
        f"reviews/chapter_{chapter:03d}_review.md",
    ]
    for rel in candidates:
        candidate = novel_path / rel
        if candidate.is_file():
            provenance[rel] = _sha256_file(candidate)
    return provenance


# --------------------------------------------------------------------------- #
# SyncReport + the headline commit() interface
# --------------------------------------------------------------------------- #


@dataclass
class SyncReport:
    """Result of a chapter sync (design #10: ``commit -> SyncReport``)."""

    chapter: int
    gate_passed: bool
    blocked: bool
    commit_id: Optional[str] = None
    idempotent: bool = False
    gate_score: Optional[float] = None
    gate_outcome: Optional[str] = None
    stages: list[SyncStageResult] = field(default_factory=list)
    updated_docs: list[str] = field(default_factory=list)
    reindex: dict[str, Any] = field(default_factory=dict)
    episodic: dict[str, Any] = field(default_factory=dict)
    rotation: Optional[dict[str, Any]] = None
    style_audit: Optional[dict[str, Any]] = None
    graph: Optional[dict[str, Any]] = None
    seed: Optional[dict[str, Any]] = None
    provenance: dict[str, str] = field(default_factory=dict)
    doctor_issues: list[Issue] = field(default_factory=list)
    blocking_issues: list[Issue] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stages"] = [s.to_dict() for s in self.stages]
        data["doctor_issues"] = [i.to_dict() for i in self.doctor_issues]
        data["blocking_issues"] = [i.to_dict() for i in self.blocking_issues]
        return data


def commit(
    novel_path: "str | Path",
    chapter: int,
    *,
    arc: Optional[int] = None,
    pipeline_state: Optional[dict[str, Any]] = None,
) -> SyncReport:
    """Run the full sync for ``chapter`` (design.md §Components #10).

    Pipeline:
      1. **Review gate** (Stage 1, blocking) — :func:`build_commit` enforces
         :func:`review_gate_passes`; a failed gate blocks (no sync).
      2. **Ledger** (Stage 1) — accept the content-addressed commit, update
         PLAN/GOAL_TRACKER/Memory, commit episodic memory.
      3. **Indexes** (Stage 2, non-blocking) — reindex via the context engine.
      4. **Audit** (Stage 3, non-blocking) — style coherence audit every
         ``N % 10 == 0``; memory rotation when over the word budget.
      5. **Provenance** — fingerprint output artifacts onto the commit.
      6. **Doctor** — block when a blocking issue remains (Requirement 11.2).
      7. **Rolling seed** — when a serialised ``pipeline_state`` is supplied,
         seed the next window (Requirement 10.3).

    Returns a :class:`SyncReport`. When the gate blocks, the report has
    ``gate_passed=False`` / ``blocked=True`` and no later stage runs.
    """
    novel_path = Path(novel_path)
    report = SyncReport(chapter=chapter, gate_passed=False, blocked=True)

    # ---- Stage 1: commit_ledger (BLOCKING) -------------------------------- #
    try:
        built = build_commit(novel_path, chapter, arc=arc)
    except ReviewGateFailed as exc:
        report.gate_score = exc.score
        report.gate_outcome = exc.outcome
        report.error = str(exc)
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_LEDGER.value,
                success=False,
                blocking=True,
                error=str(exc),
                details={"reason": "review_gate_failed"},
            )
        )
        return report
    except (ValueError, json.JSONDecodeError) as exc:
        report.error = str(exc)
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_LEDGER.value,
                success=False,
                blocking=True,
                error=str(exc),
                details={"reason": "invalid_review"},
            )
        )
        return report
    except (FileNotFoundError, OSError) as exc:
        report.error = str(exc)
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_LEDGER.value,
                success=False,
                blocking=True,
                error=str(exc),
                details={"reason": "missing_artifact"},
            )
        )
        return report

    report.gate_passed = True
    report.gate_score = built.review_score
    report.gate_outcome = built.review_outcome

    source_file = novel_path / built.source_path if built.source_path else _chapter_file(novel_path, chapter)
    review_file = novel_path / built.review_path if built.review_path else _legacy_review_source(novel_path, chapter)
    attempt = 1
    if review_file.suffix == ".json":
        try:
            attempt = int(json.loads(review_file.read_text(encoding="utf-8")).get("attempt", 1) or 1)
        except (OSError, ValueError, json.JSONDecodeError):
            attempt = 1
    manifest = _initial_manifest(
        novel_path,
        built,
        attempt=attempt,
        source_file=source_file,
        review_file=review_file,
    )
    manifest_path = _transaction_manifest_path(novel_path, chapter, attempt)
    manifest["completed_substeps"].append("validated")
    _atomic_write_json(manifest_path, manifest)

    canon_file = _chapter_file(novel_path, chapter)
    if source_file != canon_file:
        _atomic_write_text(canon_file, source_file.read_text(encoding="utf-8"))
    manifest["completed_substeps"].append("canon_promoted")
    manifest["staged_output_hashes"][_relative(novel_path, canon_file)] = _sha256_file(canon_file)
    _atomic_write_json(manifest_path, manifest)

    persisted, created = accept_commit(novel_path, built)
    report.commit_id = persisted.commit_id
    report.idempotent = not created
    manifest["commit_id"] = persisted.commit_id

    report.updated_docs = update_planning_docs(novel_path, persisted)
    report.episodic = commit_episodic(novel_path, persisted)
    for rel in report.updated_docs:
        path = novel_path / rel
        if path.exists():
            manifest["staged_output_hashes"][rel] = _sha256_file(path)
    manifest["completed_substeps"].append("commit_ledger_written")
    _atomic_write_json(manifest_path, manifest)
    report.stages.append(
        SyncStageResult(
            stage=SyncStageKind.COMMIT_LEDGER.value,
            success=True,
            blocking=True,
            details={"created": created, "updated_docs": report.updated_docs},
        )
    )

    # ---- Provenance (record fingerprints onto the commit) ----------------- #
    provenance = compute_provenance(novel_path, chapter)
    report.provenance = provenance
    persisted = ChapterCommit(
        **{**persisted.to_dict(), "provenance": provenance}  # type: ignore[arg-type]
    )
    _atomic_write_json(_commit_path(novel_path, chapter), persisted.to_dict())

    # ---- Stage 2: commit_indexes (NON-BLOCKING) --------------------------- #
    try:
        report.reindex = reindex(novel_path)
        manifest["completed_substeps"].append("derivatives_updated")
        manifest["staged_output_hashes"][RAG_INDEX_META_REL_PATH] = _sha256_file(
            novel_path / RAG_INDEX_META_REL_PATH
        )
        _atomic_write_json(manifest_path, manifest)
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_INDEXES.value,
                success=True,
                blocking=False,
                details=report.reindex,
            )
        )
    except Exception as exc:  # noqa: BLE001 — non-blocking: queue repair
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_INDEXES.value,
                success=False,
                blocking=False,
                error=str(exc),
            )
        )

    # ---- Stage 3: commit_audit (NON-BLOCKING) ----------------------------- #
    audit_details: dict[str, Any] = {}
    try:
        if style_audit_due(chapter):
            report.style_audit = _style_audit(str(novel_path), chapter)
            audit_details["style_audit"] = report.style_audit.get("status")
        rotation = get_provider().rotate(
            scope=novel_path, max_words=MEMORY_ACTIVE_MAX_WORDS
        )
        report.rotation = {
            "rotated": rotation.rotated,
            "reason": rotation.reason,
            "words_before": rotation.words_before,
            "words_after": rotation.words_after,
            "archived_total": rotation.archived_total,
        }
        audit_details["rotation"] = report.rotation
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_AUDIT.value,
                success=True,
                blocking=False,
                details=audit_details,
            )
        )
    except Exception as exc:  # noqa: BLE001 — non-blocking
        report.stages.append(
            SyncStageResult(
                stage=SyncStageKind.COMMIT_AUDIT.value,
                success=False,
                blocking=False,
                error=str(exc),
            )
        )

    # ---- Stage 4: commit_graph (NON-BLOCKING, best-effort, flag-gated) ---- #
    # Only runs — and only appears as a stage — when the ``graph`` flag is on, so
    # a flag-off sync is byte-for-byte the legacy 3-stage flow (P11). The KG is a
    # derivative rebuilt from the memory just committed above; a failure here can
    # never block an already-accepted commit (Req 7).
    graph_flag_on = False
    try:
        from tools.novelkit_longform_config import flag_enabled

        graph_flag_on = flag_enabled("graph", novel_path)
    except Exception:  # noqa: BLE001 — config optional; treat as flag-off
        graph_flag_on = False
    if graph_flag_on:
        try:
            report.graph = _maybe_build_graph(novel_path, chapter)
            report.stages.append(
                SyncStageResult(
                    stage="commit_graph",
                    success=report.graph is not None,
                    blocking=False,
                    details={"built": report.graph is not None},
                )
            )
        except Exception as exc:  # noqa: BLE001 — non-blocking derivative KG
            report.stages.append(
                SyncStageResult(
                    stage="commit_graph",
                    success=False,
                    blocking=False,
                    error=str(exc),
                )
            )

    # ---- Doctor (block on remaining blocking issues) ---------------------- #
    report.doctor_issues = health_check(novel_path)
    report.blocking_issues = classify_blocking(report.doctor_issues)
    report.blocked = bool(report.blocking_issues)
    manifest["status"] = "blocked" if report.blocked else "sync_completed"
    if "sync_completed" not in manifest["completed_substeps"] and not report.blocked:
        manifest["completed_substeps"].append("sync_completed")
    _atomic_write_json(manifest_path, manifest)

    # ---- Rolling seed (Requirement 10.3) ---------------------------------- #
    if pipeline_state is not None and not report.blocked:
        # Best-effort (Req 4.4 / Req 7): when the KG surfaced hard contradictions,
        # enqueue a rewrite item per affected chapter onto the supplied state
        # *before* seeding the next window. Never touches the review gate and
        # never breaks the seed.
        hard = (
            (report.graph or {}).get("contradictions", {}).get("hard", [])
            if report.graph
            else []
        )
        if hard:
            try:
                from tools.novelkit_graph_tool import apply_contradictions

                applied = apply_contradictions(novel_path, pipeline_state, hard)
                pipeline_state = applied["state"]
            except Exception:  # noqa: BLE001 — derivative; never break the seed
                pass
        engine = PipelineEngine(PipelineState.from_dict(pipeline_state))
        plan = engine.rolling_seed()
        report.seed = {**plan.to_dict(), "state": engine.state.to_dict()}

    return report


def _append_substep_once(manifest: dict[str, Any], substep: str) -> None:
    completed = manifest.setdefault("completed_substeps", [])
    if substep not in completed:
        completed.append(substep)


def _mark_needs_user_resolution(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    manifest["status"] = "needs_user_resolution"
    manifest["resolution_reason"] = reason
    _atomic_write_json(manifest_path, manifest)
    return {"scope": manifest_path.parent.name, "reason": reason}


def recover_transactions(novel_path: "str | Path") -> dict[str, Any]:
    """Resume incomplete sync transactions from their durable manifest.

    Recovery is intentionally conservative: it only resumes transactions that
    already reached ``canon_promoted`` and whose current canon file still
    matches the staged hash in the manifest. A hash mismatch means another
    writer/user changed canon after the crash, so the transaction is marked
    ``needs_user_resolution`` instead of guessing.
    """
    novel_path = Path(novel_path)
    transactions_dir = novel_path / "logs" / "transactions"
    report: dict[str, list[Any]] = {
        "recovered": [],
        "needs_user_resolution": [],
        "skipped": [],
    }
    if not transactions_dir.is_dir():
        return report

    for manifest_path in sorted(transactions_dir.glob("*/manifest.json")):
        scope = manifest_path.parent.name
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["needs_user_resolution"].append(
                {"scope": scope, "reason": f"invalid manifest: {exc}"}
            )
            continue

        status = str(manifest.get("status") or "")
        if status == "sync_completed":
            report["skipped"].append(scope)
            continue
        if status == "needs_user_resolution":
            report["needs_user_resolution"].append(
                {
                    "scope": scope,
                    "reason": str(
                        manifest.get("resolution_reason")
                        or "already marked needs_user_resolution"
                    ),
                }
            )
            continue

        completed = manifest.get("completed_substeps") or []
        if "canon_promoted" not in completed:
            report["skipped"].append(scope)
            continue

        canon_rel = str(manifest.get("expected_canon_path") or "")
        staged_hashes = manifest.get("staged_output_hashes") or {}
        expected_canon_hash = staged_hashes.get(canon_rel)
        canon_path = novel_path / canon_rel
        if not canon_rel or not isinstance(expected_canon_hash, str):
            report["needs_user_resolution"].append(
                _mark_needs_user_resolution(
                    manifest_path,
                    manifest,
                    reason="manifest missing staged canon hash",
                )
            )
            continue
        if not canon_path.exists() or _sha256_file(canon_path) != expected_canon_hash:
            report["needs_user_resolution"].append(
                _mark_needs_user_resolution(
                    manifest_path,
                    manifest,
                    reason="canon hash differs from transaction manifest",
                )
            )
            continue

        try:
            chapter = int(manifest["chapter"])
            built = build_commit(novel_path, chapter)
            commit_id = str(manifest.get("commit_id") or built.commit_id)
            built = ChapterCommit.from_dict(
                {**built.to_dict(), "commit_id": commit_id}
            )
            persisted, created = accept_commit(novel_path, built)
            manifest["commit_id"] = persisted.commit_id

            updated_docs = update_planning_docs(novel_path, persisted)
            commit_episodic(novel_path, persisted)
            for rel in updated_docs:
                path = novel_path / rel
                if path.exists():
                    staged_hashes[rel] = _sha256_file(path)
            manifest["staged_output_hashes"] = staged_hashes
            _append_substep_once(manifest, "commit_ledger_written")
            _atomic_write_json(manifest_path, manifest)

            provenance = compute_provenance(novel_path, chapter)
            persisted = ChapterCommit.from_dict(
                {**persisted.to_dict(), "provenance": provenance}
            )
            _atomic_write_json(_commit_path(novel_path, chapter), persisted.to_dict())

            reindex(novel_path)
            if (novel_path / RAG_INDEX_META_REL_PATH).exists():
                staged_hashes[RAG_INDEX_META_REL_PATH] = _sha256_file(
                    novel_path / RAG_INDEX_META_REL_PATH
                )
            manifest["staged_output_hashes"] = staged_hashes
            _append_substep_once(manifest, "derivatives_updated")

            blocking = classify_blocking(health_check(novel_path))
            manifest["status"] = "blocked" if blocking else "sync_completed"
            if not blocking:
                _append_substep_once(manifest, "sync_completed")
            manifest["idempotent_recovery"] = not created
            _atomic_write_json(manifest_path, manifest)
            report["recovered"].append(scope)
        except Exception as exc:  # noqa: BLE001 — recovery must fail closed.
            report["needs_user_resolution"].append(
                _mark_needs_user_resolution(
                    manifest_path,
                    manifest,
                    reason=f"recovery failed: {exc}",
                )
            )

    return report


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_SYNC_TOOL_SCHEMA = {
    "name": "novelkit_sync",
    "description": (
        "Sync / memory-commit + doctor: enforce the review gate, update "
        "PLAN/GOAL_TRACKER/Memory, reindex retrieval, commit episodic memory, "
        "run the doctor health-check, record provenance, and seed the rolling "
        "window. action='doctor' returns the health-check issues. "
        "action='recover' resumes incomplete transaction manifests."
    ),
    "input": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["commit", "doctor", "recover", "stamp_human_approval"],
            },
            "novel_path": {"type": "string"},
            "chapter": {"type": ["integer", "null"]},
            "arc": {"type": ["integer", "null"]},
            "pipeline_state": {"type": ["object", "null"]},
            "approver": {"type": ["string", "null"]},
        },
        "required": ["action", "novel_path"],
    },
    "output": {"type": "object"},
}


def sync_tool(
    action: str,
    novel_path: str,
    *,
    chapter: Optional[int] = None,
    arc: Optional[int] = None,
    pipeline_state: Optional[dict[str, Any]] = None,
    approver: Optional[str] = None,
) -> dict[str, Any]:
    """Stateless tool entrypoint: ``commit`` a chapter or run the ``doctor``."""
    if action == "commit":
        if chapter is None:
            raise ValueError("commit requires 'chapter'")
        return commit(
            novel_path, int(chapter), arc=arc, pipeline_state=pipeline_state
        ).to_dict()
    if action == "doctor":
        issues = health_check(novel_path)
        return {
            "issues": [i.to_dict() for i in issues],
            "blocking_issues": [i.to_dict() for i in classify_blocking(issues)],
        }
    if action == "recover":
        return recover_transactions(novel_path)
    if action == "stamp_human_approval":
        if chapter is None:
            raise ValueError("stamp_human_approval requires 'chapter'")
        return stamp_human_approval(Path(novel_path), int(chapter), approver=approver)
    raise ValueError(
        f"unknown action {action!r}; expected "
        "commit|doctor|recover|stamp_human_approval"
    )


registry.register(
    "novelkit_sync",
    sync_tool,
    schema=_SYNC_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "SyncStageKind",
    "BlockingPolicy",
    "SyncStageSpec",
    "SyncStageResult",
    "SYNC_STAGES",
    "Issue",
    "classify_blocking",
    "ReviewGateFailed",
    "ChapterCommit",
    "build_commit",
    "load_commit",
    "accept_commit",
    "update_planning_docs",
    "reindex",
    "commit_episodic",
    "compute_provenance",
    "health_check",
    "SyncReport",
    "commit",
    "recover_transactions",
    "sync_tool",
    "MEMORY_ACTIVE_MAX_WORDS",
    "REVIEW_PASS_SCORE",
]
