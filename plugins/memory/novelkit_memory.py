#!/usr/bin/env python3
"""novelkit_memory — unified Hermes memory-provider plugin (single-select).

This module consolidates NovelKit's sprawling ``memory_*.py`` subsystem
(``memory_store`` / ``memory_rotation`` / ``memory_compactor`` /
``memory_importance`` / ``memory_pack`` / ``memory_render`` /
``memory_resilience`` / ``memory_writer_v2`` / ``memory_item``) into **one**
memory-provider plugin with clearly-scoped internal sections (finding D4).

Design references (``.kiro/specs/novelkit-hermes-migration/design.md``):

* §"Components and Interfaces" #11 — memory-provider responsibilities and the
  ``add`` / ``search`` / ``build_context`` / ``rotate`` interface.
* §"Data Models" — the five memory layers A-E and the itemized fact model.
* §"Correctness Properties" — P7 (per-novel isolation) and P8 (rotation
  invariant: active ≤ MEMORY_ACTIVE_MAX_WORDS, resolved state archived, total
  information preserved).

The five layers (Requirement 13.1) are modelled as follows:

    A canon files     — source of truth, file-first, NEVER index-overridden.
    B RAG (FTS)        — derivative (served by the context-engine plugin).
    C vector semantic  — derivative (served by the context-engine plugin).
    D episodic         — itemized facts in the single per-novel store; a
                         *layer*, not a separate store (finding D3).
    E curated long-term— rendered ``memory/Memory.md`` view + rotation/archive.

Decisions baked in:

* **Keep writer_v2, drop the legacy duplicate writer** (D4): the episodic
  commit path here mirrors ``memory_writer_v2`` only.
* **Episodic is a layer, not a separate store** (D3): everything lives in one
  ``memory/items.sqlite3`` per novel.
* **Per-novel isolation** (Requirement 13.3, P7): each novel gets its own
  store file keyed by ``scope`` (the novel path); no cross-novel writes.
* **Canon authority** (Requirement 13.2, P5): retrieval/index state is
  derivative and never flips canon files.

Requirements: 13, 14
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Generator, Iterable, Optional, Union

# --------------------------------------------------------------------------- #
# Constants (ported from cp_constants.py + memory_rotation.py)
# --------------------------------------------------------------------------- #

#: Active-memory rotation threshold in words (Requirement 11.3 / 13.1, P8).
MEMORY_ACTIVE_MAX_WORDS = 3500

#: Max evidence characters retained inline before hashing to a reference.
MEMORY_EVIDENCE_MAX_CHARS = 280

#: On-disk schema version for the itemized store.
MEMORY_STORE_SCHEMA_VERSION = 1

#: Default approximate token budget for the semantic slice of a memory pack.
MEMORY_SEMANTIC_TOKEN_BUDGET_DEFAULT = 1500

MEMORY_CATEGORY_VALUES: tuple[str, ...] = (
    "character_state",
    "story_facts",
    "world_rules",
    "timeline",
    "open_loops",
    "reader_promises",
    "relationships",
    "minor_cast",
)

MEMORY_STATUS_VALUES: tuple[str, ...] = (
    "active",
    "outdated",
    "contradicted",
    "tentative",
)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


class Category(str, Enum):
    """Itemized memory categories (matches MEMORY_CATEGORY_VALUES)."""

    CHARACTER_STATE = "character_state"
    STORY_FACTS = "story_facts"
    WORLD_RULES = "world_rules"
    TIMELINE = "timeline"
    OPEN_LOOPS = "open_loops"
    READER_PROMISES = "reader_promises"
    RELATIONSHIPS = "relationships"
    MINOR_CAST = "minor_cast"


class Status(str, Enum):
    """Itemized memory status values (matches MEMORY_STATUS_VALUES)."""

    ACTIVE = "active"
    OUTDATED = "outdated"
    CONTRADICTED = "contradicted"
    TENTATIVE = "tentative"


class MemoryLayer(str, Enum):
    """The five memory layers (design §Data Models).

    A and the derivative B/C/D/E layers all answer through this single
    provider; episodic (D) is a *layer* over the one shared store, not a
    separate database (finding D3).
    """

    A_CANON = "canon"  # source of truth, file-first, never overridden
    B_RAG = "rag"  # derivative full-text
    C_VECTOR = "vector"  # derivative semantic
    D_EPISODIC = "episodic"  # session/arc itemized facts (this store)
    E_CURATED = "curated"  # curated long-term (Memory.md)


#: Layers whose state is derivative and must never override canon (P5).
DERIVATIVE_LAYERS = frozenset(
    {MemoryLayer.B_RAG, MemoryLayer.C_VECTOR, MemoryLayer.D_EPISODIC, MemoryLayer.E_CURATED}
)


# --------------------------------------------------------------------------- #
# MemoryItem data model (ported from memory_item.py)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MemoryItem:
    """A single itemized memory fact."""

    id: str
    category: Category
    subject: str
    field: str
    value: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: Status = Status.ACTIVE
    source_chapter: Optional[int] = None
    source_commit_id: Optional[str] = None
    evidence: str = ""
    created_at: str = ""
    updated_at: str = ""


_SUBJECT_FIELD_CATEGORIES = frozenset(
    {
        Category.CHARACTER_STATE,
        Category.WORLD_RULES,
        Category.STORY_FACTS,
        Category.TIMELINE,
        Category.RELATIONSHIPS,
    }
)
_SUBJECT_ONLY_CATEGORIES = frozenset(
    {Category.OPEN_LOOPS, Category.READER_PROMISES, Category.MINOR_CAST}
)


def _merge_minor_cast_payload(
    existing: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    """Monotonic merge for a minor-cast roster entry (Req 6; P18).

    ``first_seen`` takes the min, ``last_seen``/``appearance_count`` take the
    max, and a non-empty ``brief_role`` from the candidate wins. This keeps the
    roster monotonic even when two commits carry the same ``value``.
    """
    merged = dict(existing)
    if candidate.get("brief_role"):
        merged["brief_role"] = candidate["brief_role"]
    first = [
        v
        for v in (existing.get("first_seen"), candidate.get("first_seen"))
        if isinstance(v, int)
    ]
    if first:
        merged["first_seen"] = min(first)
    last = [
        v
        for v in (existing.get("last_seen"), candidate.get("last_seen"))
        if isinstance(v, int)
    ]
    if last:
        merged["last_seen"] = max(last)
    count = [
        v
        for v in (existing.get("appearance_count"), candidate.get("appearance_count"))
        if isinstance(v, int)
    ]
    if count:
        merged["appearance_count"] = max(count)
    return merged


def dedupe_key(item: MemoryItem) -> str:
    """Category-specific dedupe key (category prefix → global uniqueness)."""
    if item.category in _SUBJECT_FIELD_CATEGORIES:
        return f"{item.category.value}:{item.subject}:{item.field}"
    if item.category in _SUBJECT_ONLY_CATEGORIES:
        return f"{item.category.value}:{item.subject}"
    raise ValueError(f"Unknown category: {item.category!r}")


def normalize_relationship_subject(a: str, b: str) -> str:
    """Canonical ``A↔B`` label, names sorted case-insensitively."""
    lo, hi = sorted([a, b], key=lambda n: n.lower())
    return f"{lo}↔{hi}"


def truncate_evidence(text: str) -> tuple[str, Optional[dict[str, Any]]]:
    """Truncate evidence to MEMORY_EVIDENCE_MAX_CHARS, hashing the overflow."""
    import hashlib

    if len(text) <= MEMORY_EVIDENCE_MAX_CHARS:
        return (text, None)
    full_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (text[:MEMORY_EVIDENCE_MAX_CHARS], {"evidence_ref": full_hash})


def item_to_dict(item: MemoryItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "category": item.category.value,
        "subject": item.subject,
        "field": item.field,
        "value": item.value,
        "payload": item.payload,
        "status": item.status.value,
        "source_chapter": item.source_chapter,
        "source_commit_id": item.source_commit_id,
        "evidence": item.evidence,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def item_from_dict(data: dict[str, Any]) -> MemoryItem:
    return MemoryItem(
        id=data["id"],
        category=Category(data["category"]),
        subject=data["subject"],
        field=data["field"],
        value=data["value"],
        payload=data.get("payload", {}) or {},
        status=Status(data["status"]),
        source_chapter=data.get("source_chapter"),
        source_commit_id=data.get("source_commit_id"),
        evidence=data.get("evidence", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )


# --------------------------------------------------------------------------- #
# Word counting + rendering helpers (ported from memory_rotation.py)
# --------------------------------------------------------------------------- #


def word_count(text: str) -> int:
    """Unicode-aware word count (mirrors memory_rotation._word_count)."""
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def render_item_text(item: MemoryItem) -> str:
    """Render a single item to the textual form used for word accounting."""
    parts = [item.subject, item.field, item.value, item.evidence]
    return " ".join(p for p in parts if p)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# Importance scoring (compact port of memory_importance.py)
# --------------------------------------------------------------------------- #

_CALLBACK_KEYWORDS = (
    "hứa", "nợ", "thề", "chưa trả", "bí mật", "giấu", "mầm", "manh mối",
    "promise", "debt", "seed", "foreshadow", "unresolved", "dormant",
    "pending", "owe", "secret", "hận", "thù", "ân", "nghĩa", "ước",
    "phong ấn", "tiên tri", "lời nguyền",
)
_HIGH_IMPORTANCE_KEYWORDS = (
    "core wound", "vết thương cốt lõi", "nhân vật chính", "đột phá",
    "breakthrough", "phản bội", "betrayal", "revelation", "chết", "death",
    "pháp bảo", "thần khí", "artifact", "world rule", "luật thế giới", "taboo",
)
#: Categories that carry long-term narrative weight and resist archiving.
_DURABLE_CATEGORIES = frozenset(
    {Category.WORLD_RULES, Category.OPEN_LOOPS, Category.READER_PROMISES, Category.RELATIONSHIPS}
)


def importance_score(item: MemoryItem) -> float:
    """Deterministic narrative-importance score in ``[0.0, 1.0]``.

    Higher means "keep in active memory longer". Used by rotation to choose
    which surplus active items to archive first (lowest importance first).
    """
    text = f"{item.subject} {item.field} {item.value} {item.evidence}".lower()
    score = 0.0
    if any(kw in text for kw in _CALLBACK_KEYWORDS):
        score += 0.35
    if any(kw in text for kw in _HIGH_IMPORTANCE_KEYWORDS):
        score += 0.35
    if item.category in _DURABLE_CATEGORIES:
        score += 0.2
    # Explicit confidence nudges importance up.
    confidence = item.payload.get("confidence")
    if isinstance(confidence, (int, float)) and confidence >= 0.7:
        score += 0.1
    return min(1.0, score)


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #


class ItemStoreSchemaMismatch(Exception):
    """On-disk schema version is newer than this runtime understands."""


class ItemStoreLocked(Exception):
    """A write could not acquire the store lock (SQLITE_BUSY)."""


# --------------------------------------------------------------------------- #
# UpsertResult
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class UpsertResult:
    """Outcome counts from a single :meth:`_ItemStore.upsert_many` call."""

    inserted: int = 0
    updated: int = 0
    outdated: int = 0
    contradicted: int = 0
    tentative_replaced: int = 0
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Per-novel SQLite item store (unifies memory_store + archive for rotation)
# --------------------------------------------------------------------------- #

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS memory_items (
    id               TEXT PRIMARY KEY,
    category         TEXT NOT NULL,
    subject          TEXT NOT NULL,
    field            TEXT NOT NULL,
    value            TEXT NOT NULL,
    payload          TEXT NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL,
    source_chapter   INTEGER,
    source_commit_id TEXT,
    evidence         TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_category_subject_field
    ON memory_items(category, subject, field);
CREATE INDEX IF NOT EXISTS idx_items_status_category
    ON memory_items(status, category);
CREATE INDEX IF NOT EXISTS idx_items_updated_at
    ON memory_items(updated_at);

-- Archive table holds rotated-out facts; total information across
-- memory_items ∪ memory_archive is conserved (P8).
CREATE TABLE IF NOT EXISTS memory_archive (
    id               TEXT PRIMARY KEY,
    category         TEXT NOT NULL,
    subject          TEXT NOT NULL,
    field            TEXT NOT NULL,
    value            TEXT NOT NULL,
    payload          TEXT NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL,
    source_chapter   INTEGER,
    source_commit_id TEXT,
    evidence         TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    archived_at      TEXT NOT NULL,
    archived_reason  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS memory_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_META_SEED = {
    "schema_version": str(MEMORY_STORE_SCHEMA_VERSION),
    "bootstrap_completed_at": "",
    "last_rotation_at": "",
}

_ITEM_COLUMNS = (
    "id, category, subject, field, value, payload, status, "
    "source_chapter, source_commit_id, evidence, created_at, updated_at"
)


def _row_to_item(row: tuple) -> MemoryItem:
    return item_from_dict(
        {
            "id": row[0],
            "category": row[1],
            "subject": row[2],
            "field": row[3],
            "value": row[4],
            "payload": json.loads(row[5]) if row[5] else {},
            "status": row[6],
            "source_chapter": row[7],
            "source_commit_id": row[8],
            "evidence": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }
    )


class _ItemStore:
    """SQLite-backed itemized store scoped to a single novel directory.

    The store path is derived purely from ``novel_path`` which guarantees
    **per-novel isolation** (P7): two different novels resolve to two
    different database files and can never write to each other.
    """

    def __init__(self, novel_path: Path) -> None:
        self.novel_path = Path(novel_path)
        self.db_path = self.novel_path / "memory" / "items.sqlite3"
        self._init_store()

    # -- lifecycle -------------------------------------------------------- #

    def _init_store(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(_SCHEMA_SQL)
            for key, value in _META_SEED.items():
                conn.execute(
                    "INSERT OR IGNORE INTO memory_meta (key, value) VALUES (?, ?)",
                    (key, value),
                )
            self._check_schema_version(conn)
            conn.commit()
        finally:
            conn.close()

    def _check_schema_version(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT value FROM memory_meta WHERE key = 'schema_version'"
        ).fetchone()
        disk_ver = int(row[0]) if row else 0
        if disk_ver > MEMORY_STORE_SCHEMA_VERSION:
            raise ItemStoreSchemaMismatch(
                f"on-disk {disk_ver} > runtime {MEMORY_STORE_SCHEMA_VERSION}"
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
        except sqlite3.OperationalError as exc:  # pragma: no cover - lock path
            if "database is locked" in str(exc):
                raise ItemStoreLocked(str(exc)) from exc
            raise
        finally:
            conn.close()

    def _set_meta(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO memory_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    # -- writes ----------------------------------------------------------- #

    def _insert(self, conn: sqlite3.Connection, item: MemoryItem, now: str) -> None:
        created = item.created_at or now
        conn.execute(
            f"INSERT INTO memory_items ({_ITEM_COLUMNS}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item.id,
                item.category.value,
                item.subject,
                item.field,
                item.value,
                json.dumps(item.payload, ensure_ascii=False),
                item.status.value,
                item.source_chapter,
                item.source_commit_id,
                item.evidence,
                created,
                now,
            ),
        )

    def _set_status(
        self, conn: sqlite3.Connection, item_id: str, status: str, now: str
    ) -> None:
        conn.execute(
            "UPDATE memory_items SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, item_id),
        )

    def _find_active_match(
        self, conn: sqlite3.Connection, key: str
    ) -> Optional[MemoryItem]:
        # dedupe_key is category[:subject[:field]]; reconstruct the filter.
        parts = key.split(":")
        category = parts[0]
        subject = parts[1]
        if len(parts) == 3:
            sql = (
                f"SELECT {_ITEM_COLUMNS} FROM memory_items "
                "WHERE category = ? AND subject = ? AND field = ? "
                "AND status IN ('active', 'tentative') LIMIT 1"
            )
            params: tuple = (category, subject, parts[2])
        else:
            sql = (
                f"SELECT {_ITEM_COLUMNS} FROM memory_items "
                "WHERE category = ? AND subject = ? "
                "AND status IN ('active', 'tentative') LIMIT 1"
            )
            params = (category, subject)
        row = conn.execute(sql, params).fetchone()
        return _row_to_item(row) if row else None

    def upsert_many(self, items: Iterable[MemoryItem]) -> UpsertResult:
        """Apply dedupe + contradiction rules (ported from memory_store)."""
        now = _now_iso()
        inserted = updated = outdated = contradicted = tentative_replaced = 0
        warnings: list[str] = []

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for candidate in items:
                    key = dedupe_key(candidate)
                    existing = self._find_active_match(conn, key)

                    if existing is not None and candidate.category == Category.MINOR_CAST:
                        merged = _merge_minor_cast_payload(
                            existing.payload, candidate.payload
                        )
                        new_value = candidate.value or existing.value
                        # A tentative roster entry must be promoted to active on
                        # merge; otherwise it would stay tentative forever and
                        # never surface via iter_active/recent_cast (parity with
                        # the general tentative→active promotion path below).
                        promote = existing.status == Status.TENTATIVE
                        if (
                            merged == existing.payload
                            and new_value == existing.value
                            and not promote
                        ):
                            continue  # idempotent (no churn)
                        conn.execute(
                            "UPDATE memory_items SET value=?, payload=?, status=?, "
                            "source_chapter=?, source_commit_id=?, updated_at=? "
                            "WHERE id=?",
                            (
                                new_value,
                                json.dumps(merged, ensure_ascii=False),
                                Status.ACTIVE.value,
                                candidate.source_chapter,
                                candidate.source_commit_id,
                                now,
                                existing.id,
                            ),
                        )
                        if promote:
                            tentative_replaced += 1
                        else:
                            updated += 1
                        continue

                    if existing is None:
                        self._insert(conn, candidate, now)
                        inserted += 1
                        continue

                    if existing.status == Status.TENTATIVE:
                        conn.execute(
                            "UPDATE memory_items SET category=?, subject=?, "
                            "field=?, value=?, payload=?, status=?, "
                            "source_chapter=?, source_commit_id=?, evidence=?, "
                            "updated_at=? WHERE id=?",
                            (
                                candidate.category.value,
                                candidate.subject,
                                candidate.field,
                                candidate.value,
                                json.dumps(candidate.payload, ensure_ascii=False),
                                Status.ACTIVE.value,
                                candidate.source_chapter,
                                candidate.source_commit_id,
                                candidate.evidence,
                                now,
                                existing.id,
                            ),
                        )
                        tentative_replaced += 1
                        continue

                    # existing is active
                    if existing.value == candidate.value:
                        continue  # idempotent

                    existing_conf = existing.payload.get("confidence", 0.5)
                    candidate_conf = candidate.payload.get("confidence", 0.5)
                    if existing_conf >= 0.7 and candidate_conf >= 0.7:
                        self._set_status(
                            conn, existing.id, Status.CONTRADICTED.value, now
                        )
                        self._insert(
                            conn,
                            MemoryItem(
                                id=candidate.id,
                                category=candidate.category,
                                subject=candidate.subject,
                                field=candidate.field,
                                value=candidate.value,
                                payload=candidate.payload,
                                status=Status.CONTRADICTED,
                                source_chapter=candidate.source_chapter,
                                source_commit_id=candidate.source_commit_id,
                                evidence=candidate.evidence,
                                created_at=candidate.created_at,
                                updated_at=now,
                            ),
                            now,
                        )
                        contradicted += 2
                        warnings.append(
                            f"Contradiction: {key} — existing={existing.id}, new={candidate.id}"
                        )
                    else:
                        self._set_status(conn, existing.id, Status.OUTDATED.value, now)
                        self._insert(conn, candidate, now)
                        updated += 1
                        outdated += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return UpsertResult(
            inserted=inserted,
            updated=updated,
            outdated=outdated,
            contradicted=contradicted,
            tentative_replaced=tentative_replaced,
            warnings=warnings,
        )

    # -- reads ------------------------------------------------------------ #

    def all_items(self) -> list[MemoryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_ITEM_COLUMNS} FROM memory_items"
            ).fetchall()
        return [_row_to_item(r) for r in rows]

    def iter_active(self, *, category: Optional[str] = None) -> list[MemoryItem]:
        sql = f"SELECT {_ITEM_COLUMNS} FROM memory_items WHERE status = 'active'"
        params: tuple = ()
        if category is not None:
            sql += " AND category = ?"
            params = (category,)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_item(r) for r in rows]

    def query(
        self,
        *,
        category: Optional[str] = None,
        subject: Optional[str] = None,
        field: Optional[str] = None,
        status: Optional[str] = None,
        text: Optional[str] = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        clauses: list[str] = []
        params: list[Any] = []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if subject is not None:
            clauses.append("subject = ?")
            params.append(subject)
        if field is not None:
            clauses.append("field = ?")
            params.append(field)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if text:
            clauses.append("(subject LIKE ? OR field LIKE ? OR value LIKE ?)")
            like = f"%{text}%"
            params.extend([like, like, like])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT {_ITEM_COLUMNS} FROM memory_items {where} LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_item(r) for r in rows]

    def archived_items(self) -> list[MemoryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_ITEM_COLUMNS} FROM memory_archive"
            ).fetchall()
        return [_row_to_item(r) for r in rows]

    def active_word_count(self) -> int:
        """Word count of all currently-live items (the 'active memory')."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT subject, field, value, evidence FROM memory_items"
            ).fetchall()
        text = " ".join(" ".join(p for p in row if p) for row in rows)
        return word_count(text)

    # -- archive (rotation primitive) ------------------------------------- #

    def archive(self, items: Iterable[MemoryItem], *, reason: str) -> int:
        """Move ``items`` from ``memory_items`` to ``memory_archive``.

        Insertion into the archive happens before deletion from the live
        table, inside one transaction, so no fact can be lost in between.
        """
        now = _now_iso()
        moved = 0
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for item in items:
                    conn.execute(
                        f"INSERT OR REPLACE INTO memory_archive "
                        f"({_ITEM_COLUMNS}, archived_at, archived_reason) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            item.id,
                            item.category.value,
                            item.subject,
                            item.field,
                            item.value,
                            json.dumps(item.payload, ensure_ascii=False),
                            item.status.value,
                            item.source_chapter,
                            item.source_commit_id,
                            item.evidence,
                            item.created_at,
                            item.updated_at,
                            now,
                            reason,
                        ),
                    )
                    conn.execute(
                        "DELETE FROM memory_items WHERE id = ?", (item.id,)
                    )
                    moved += 1
                self._set_meta(conn, "last_rotation_at", now)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return moved


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RotationReport:
    """Result of a :meth:`NovelKitMemoryProvider.rotate` call."""

    rotated: bool
    reason: str
    words_before: int
    words_after: int
    archived_resolved: int = 0
    archived_surplus: int = 0

    @property
    def archived_total(self) -> int:
        return self.archived_resolved + self.archived_surplus


@dataclass
class MemoryPack:
    """Composed read-only payload returned by :meth:`build_context`."""

    working_memory: list[dict] = field(default_factory=list)
    episodic_memory: list[dict] = field(default_factory=list)
    semantic_memory: list[dict] = field(default_factory=list)
    active_constraints: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Memory-provider ABC (mirrors the Hermes memory-provider contract)
# --------------------------------------------------------------------------- #

Scope = Union[str, Path]


class MemoryProvider(ABC):
    """Abstract memory-provider plugin interface (single-select).

    Mirrors the Hermes memory-provider ABC referenced in design §11:
    ``add`` / ``search`` / ``build_context`` / ``rotate``. Every method is
    scoped to a single novel so the provider can serve many novels while
    keeping their state isolated (P7).
    """

    @abstractmethod
    def add(self, memory: Union[MemoryItem, dict], *, scope: Scope) -> UpsertResult:
        ...

    @abstractmethod
    def search(
        self, query: str, *, scope: Scope, layer: Optional[MemoryLayer] = None, limit: int = 50
    ) -> list[MemoryItem]:
        ...

    @abstractmethod
    def build_context(self, query: str, *, scope: Scope, max_tokens: int) -> MemoryPack:
        ...

    @abstractmethod
    def rotate(
        self, *, scope: Scope, max_words: int = MEMORY_ACTIVE_MAX_WORDS
    ) -> RotationReport:
        ...


# --------------------------------------------------------------------------- #
# Concrete provider
# --------------------------------------------------------------------------- #


def _estimate_tokens(text: str) -> int:
    return len(text.split())


def _coerce_item(memory: Union[MemoryItem, dict]) -> MemoryItem:
    """Normalise a raw fact dict (writer_v2 style) into a MemoryItem."""
    if isinstance(memory, MemoryItem):
        item = memory
    else:
        category = memory.get("category")
        category = category if isinstance(category, Category) else Category(category)
        evidence_raw = memory.get("evidence", "") or ""
        evidence, patch = truncate_evidence(evidence_raw)
        payload = dict(memory.get("payload", {}) or {})
        confidence = memory.get("confidence")
        if confidence is not None and "confidence" not in payload:
            payload["confidence"] = confidence
        if patch:
            payload.update(patch)
        status = memory.get("status", Status.ACTIVE)
        status = status if isinstance(status, Status) else Status(status)
        item = MemoryItem(
            id=memory.get("id") or uuid.uuid4().hex,
            category=category,
            subject=memory.get("subject", ""),
            field=memory.get("field", ""),
            value=memory.get("value", ""),
            payload=payload,
            status=status,
            source_chapter=memory.get("source_chapter"),
            source_commit_id=memory.get("source_commit_id"),
            evidence=evidence,
            created_at=memory.get("created_at", ""),
            updated_at=memory.get("updated_at", ""),
        )
    if not item.subject or not item.value:
        raise ValueError("memory fact requires non-empty subject and value")
    return item


class NovelKitMemoryProvider(MemoryProvider):
    """Unified five-layer memory provider with per-novel isolation.

    Stores are cached per resolved novel path. Because the store path is a
    pure function of ``scope``, an operation on one novel can never mutate
    another novel's store (P7).
    """

    name = "novelkit_memory"

    def __init__(self) -> None:
        self._stores: dict[Path, _ItemStore] = {}

    # -- scope / store resolution ---------------------------------------- #

    @staticmethod
    def _resolve(scope: Scope) -> Path:
        return Path(scope).expanduser().resolve()

    def store(self, scope: Scope) -> _ItemStore:
        key = self._resolve(scope)
        store = self._stores.get(key)
        if store is None:
            store = _ItemStore(key)
            self._stores[key] = store
        return store

    # -- canon authority (Layer A, P5) ----------------------------------- #

    @staticmethod
    def is_derivative(layer: MemoryLayer) -> bool:
        """Layers B-E are derivative; canon (A) is the source of truth."""
        return layer in DERIVATIVE_LAYERS

    @staticmethod
    def can_override_canon(layer: MemoryLayer) -> bool:
        """Derivative layers may never override canon files (Requirement 13.2)."""
        return layer == MemoryLayer.A_CANON

    # -- interface: add -------------------------------------------------- #

    def add(self, memory: Union[MemoryItem, dict], *, scope: Scope) -> UpsertResult:
        """Add a single fact to the episodic/working store for ``scope``."""
        return self.store(scope).upsert_many([_coerce_item(memory)])

    # -- episodic commit (writer_v2 path; layer D) ----------------------- #

    def commit_episodic(
        self,
        *,
        scope: Scope,
        memory_facts: Optional[list[dict]] = None,
        state_deltas: Optional[dict] = None,
        chapter: Optional[int] = None,
        commit_id: Optional[str] = None,
    ) -> UpsertResult:
        """Convert a chapter commit into items and upsert them (D4 keeps v2).

        ``memory_facts`` is a list of fact dicts; ``state_deltas`` is a dict
        keyed by category whose values are either a list of delta dicts or a
        flat ``field -> value`` mapping for a single subject.
        """
        commit_id = commit_id or uuid.uuid4().hex
        items: list[MemoryItem] = []
        for fact in memory_facts or []:
            enriched = {**fact, "source_chapter": chapter, "source_commit_id": commit_id}
            try:
                items.append(_coerce_item(enriched))
            except ValueError:
                continue
        for category_str, deltas in (state_deltas or {}).items():
            items.extend(
                self._deltas_to_items(category_str, deltas, chapter, commit_id)
            )
        if not items:
            return UpsertResult()
        return self.store(scope).upsert_many(items)

    @staticmethod
    def _deltas_to_items(
        category_str: Any, deltas: Any, chapter: Optional[int], commit_id: str
    ) -> list[MemoryItem]:
        try:
            category = (
                category_str
                if isinstance(category_str, Category)
                else Category(category_str)
            )
        except ValueError:
            return []
        items: list[MemoryItem] = []
        if isinstance(deltas, list):
            rows = [d for d in deltas if isinstance(d, dict)]
        elif isinstance(deltas, dict):
            subject = deltas.get("subject", str(category_str))
            rows = [
                {"subject": subject, "field": f, "value": v}
                for f, v in deltas.items()
                if f != "subject" and v
            ]
        else:
            return []
        for row in rows:
            subject = row.get("subject", "")
            value = row.get("value", "")
            if not subject or not value:
                continue
            try:
                items.append(
                    _coerce_item(
                        {
                            **row,
                            "category": category,
                            "value": str(value),
                            "source_chapter": chapter,
                            "source_commit_id": commit_id,
                        }
                    )
                )
            except ValueError:
                continue
        return items

    # -- interface: search ----------------------------------------------- #

    def search(
        self,
        query: str,
        *,
        scope: Scope,
        layer: Optional[MemoryLayer] = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """Substring search over live items (layers B/C/D are derivative).

        ``layer`` is accepted for interface compatibility; the unified store
        answers for all derivative layers from one place (D3).
        """
        return self.store(scope).query(text=query or None, limit=limit)

    # -- interface: build_context ---------------------------------------- #

    def build_context(
        self,
        query: str,
        *,
        scope: Scope,
        max_tokens: int = MEMORY_SEMANTIC_TOKEN_BUDGET_DEFAULT,
    ) -> MemoryPack:
        """Compose a retrieval-first memory pack (Requirement 13.4).

        Returns working/episodic/semantic/constraints slices drawn only from
        active items. Constraints (world rules + open loops) are always
        included; the semantic slice is keyword-filtered and trimmed to
        ``max_tokens``.
        """
        store = self.store(scope)
        active = store.iter_active()
        keywords = [w for w in re.split(r"\W+", (query or "").lower()) if w]

        working = [
            item_to_dict(i)
            for i in active
            if i.category in (Category.CHARACTER_STATE, Category.RELATIONSHIPS)
        ]
        episodic = [
            item_to_dict(i)
            for i in active
            if i.category in (Category.TIMELINE, Category.STORY_FACTS)
        ]
        constraints = [
            item_to_dict(i)
            for i in active
            if i.category in (Category.WORLD_RULES, Category.OPEN_LOOPS)
        ]

        semantic: list[dict] = []
        if keywords:
            scored: list[tuple[int, MemoryItem]] = []
            for item in active:
                hay = f"{item.subject} {item.field} {item.value}".lower()
                overlap = sum(1 for kw in keywords if kw in hay)
                if overlap:
                    scored.append((overlap, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            spent = 0
            for _overlap, item in scored:
                cost = _estimate_tokens(render_item_text(item))
                if spent + cost > max_tokens:
                    break
                semantic.append(item_to_dict(item))
                spent += cost

        return MemoryPack(
            working_memory=working,
            episodic_memory=episodic,
            semantic_memory=semantic,
            active_constraints=constraints,
            stats={
                "active_total": len(active),
                "active_words": store.active_word_count(),
                "semantic_token_budget": max_tokens,
            },
        )

    # -- interface: rotate ----------------------------------------------- #

    def rotate(
        self, *, scope: Scope, max_words: int = MEMORY_ACTIVE_MAX_WORDS
    ) -> RotationReport:
        """Rotate oversized active memory into the archive (P8).

        Algorithm (information-preserving):

        1. If active memory ≤ ``max_words`` → no-op.
        2. Archive **all resolved state** (status outdated/contradicted) — this
           is the primary thing rotation removes from the working set.
        3. If still over budget, archive surplus active/tentative items
           lowest-importance-first (ties broken by oldest ``updated_at``)
           until active memory ≤ ``max_words``.

        Every archived item is inserted into ``memory_archive`` before being
        deleted from the live table, so ``memory_items ∪ memory_archive`` after
        rotation equals the live set before rotation (total info preserved).
        """
        store = self.store(scope)
        words_before = store.active_word_count()
        if words_before <= max_words:
            return RotationReport(
                rotated=False,
                reason="below_threshold",
                words_before=words_before,
                words_after=words_before,
            )

        # Step 2: archive resolved state.
        live = store.all_items()
        resolved = [
            i for i in live if i.status in (Status.OUTDATED, Status.CONTRADICTED)
        ]
        archived_resolved = store.archive(resolved, reason="resolved_state")

        # Step 3: archive surplus working items if still over budget.
        archived_surplus = 0
        if store.active_word_count() > max_words:
            survivors = store.all_items()
            # Lowest importance first, then oldest, then stable by id.
            survivors.sort(
                key=lambda i: (importance_score(i), i.updated_at, i.id)
            )
            running = store.active_word_count()
            to_archive: list[MemoryItem] = []
            for item in survivors:
                if running <= max_words:
                    break
                to_archive.append(item)
                running -= word_count(render_item_text(item))
            if to_archive:
                archived_surplus = store.archive(
                    to_archive, reason="rotation_surplus"
                )

        words_after = store.active_word_count()
        return RotationReport(
            rotated=True,
            reason="rotated",
            words_before=words_before,
            words_after=words_after,
            archived_resolved=archived_resolved,
            archived_surplus=archived_surplus,
        )


# --------------------------------------------------------------------------- #
# Plugin registration (self-registering at import time)
# --------------------------------------------------------------------------- #

#: Process-wide singleton provider (single-select memory provider).
PROVIDER = NovelKitMemoryProvider()


def get_provider() -> NovelKitMemoryProvider:
    """Return the active memory provider singleton."""
    return PROVIDER


def recent_cast(scope: Scope, *, limit: int = 12) -> list[MemoryItem]:
    """Most-recently-active named minor characters, newest ``last_seen`` first
    (Req 6.4). Drawn from the active ``minor_cast`` layer for ``scope``."""
    items = get_provider().store(scope).query(
        category=Category.MINOR_CAST.value, status=Status.ACTIVE.value, limit=10_000
    )
    items.sort(
        key=lambda i: (i.payload.get("last_seen") or 0, i.subject), reverse=True
    )
    return items[:limit]


def _register() -> None:
    """Register provider entry points with the Hermes tool registry shim."""
    try:
        from tools import registry
    except Exception:  # pragma: no cover - registry optional in isolation
        return

    # overwrite=True keeps registration idempotent across module reloads:
    # this plugin owns the ``memory.*`` namespace as the single-select provider.
    registry.register(
        "memory.add",
        PROVIDER.add,
        module=__name__,
        schema={"type": "memory-provider", "op": "add"},
        overwrite=True,
    )
    registry.register(
        "memory.search",
        PROVIDER.search,
        module=__name__,
        schema={"type": "memory-provider", "op": "search"},
        overwrite=True,
    )
    registry.register(
        "memory.build_context",
        PROVIDER.build_context,
        module=__name__,
        schema={"type": "memory-provider", "op": "build_context"},
        overwrite=True,
    )
    registry.register(
        "memory.rotate",
        PROVIDER.rotate,
        module=__name__,
        schema={"type": "memory-provider", "op": "rotate"},
        overwrite=True,
    )


_register()
