"""User-rule snapshot helpers for the unified creative pipeline.

``PROJECT_DNA.rules.json`` is the single machine-readable snapshot of creative
user rules. This module deliberately keeps the first boundary small: load the
snapshot, canonicalise it, and expose a stable digest that Writer, self-check,
Reviewer, and sync can share.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RULES_SNAPSHOT_REL_PATH = "PROJECT_DNA.rules.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as pretty JSON atomically (temp file + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_rules_snapshot(novel_path: str | Path) -> dict[str, Any] | None:
    """Load the rule snapshot, returning ``None`` for legacy workspaces."""
    path = Path(novel_path) / RULES_SNAPSHOT_REL_PATH
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("PROJECT_DNA.rules.json must contain a JSON object")
    if data.get("schema_version") != 1:
        raise ValueError("PROJECT_DNA.rules.json schema_version must be 1")
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("PROJECT_DNA.rules.json rules must be a list")
    return data


def current_rules_digest(novel_path: str | Path) -> str | None:
    """Return ``sha256:<hex>`` for the current user-rule snapshot."""
    snapshot = load_rules_snapshot(novel_path)
    if snapshot is None:
        return None
    digest = hashlib.sha256(_canonical_json_bytes(snapshot)).hexdigest()
    return f"sha256:{digest}"


def append_rule(
    novel_path: str | Path,
    text: str,
    *,
    scope: str = "style",
    kind: str = "preference",
    source: str = "runtime_user_steer",
) -> dict[str, Any]:
    """Append a user craft/style rule to ``PROJECT_DNA.rules.json``.

    Idempotent by ``(scope, stripped text)``: re-appending the same rule is a
    no-op that returns the existing ``rule_id`` and ``changed=False``. On a real
    append the snapshot ``revision`` is bumped, ``updated_at`` refreshed, and the
    file rewritten atomically. Returns ``{rule_id, rules_digest, changed}``.

    A changed snapshot shifts ``current_rules_digest`` which, by design, forces
    any not-yet-synced typed review produced under the old rules to be
    re-validated before it can enter canon (see ``novelkit_sync_tool``).
    """
    root = Path(novel_path)
    path = root / RULES_SNAPSHOT_REL_PATH
    clean = (text or "").strip()
    if not clean:
        raise ValueError("append_rule requires non-empty text")

    snapshot = load_rules_snapshot(root)
    if snapshot is None:
        snapshot = {
            "schema_version": 1,
            "revision": 0,
            "rules": [],
            "updated_at": "",
        }
    rules = snapshot.setdefault("rules", [])
    if not isinstance(rules, list):
        raise ValueError("PROJECT_DNA.rules.json rules must be a list")

    for rule in rules:
        if (
            isinstance(rule, dict)
            and rule.get("scope") == scope
            and str(rule.get("text", "")).strip() == clean
        ):
            return {
                "rule_id": rule.get("rule_id"),
                "rules_digest": current_rules_digest(root),
                "changed": False,
            }

    rule_id = f"user_{len(rules) + 1:04d}"
    rules.append(
        {
            "rule_id": rule_id,
            "scope": scope,
            "kind": kind,
            "text": clean,
            "normalized": {},
            "enforcement": "preference",
            "source": source,
            "created_at": _now_iso(),
        }
    )
    snapshot["revision"] = int(snapshot.get("revision", 0)) + 1
    snapshot["updated_at"] = _now_iso()
    _atomic_write_json(path, snapshot)
    return {
        "rule_id": rule_id,
        "rules_digest": current_rules_digest(root),
        "changed": True,
    }


__all__ = [
    "RULES_SNAPSHOT_REL_PATH",
    "append_rule",
    "current_rules_digest",
    "load_rules_snapshot",
]
