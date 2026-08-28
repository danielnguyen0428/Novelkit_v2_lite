"""Artifact-layout mapping: NovelKit novel workspace ↔ AutoNovel workspace.

Phase 5 of the migration (Task 12.2). NovelKit's file-first canon lives under a
fixed novel layout (``PROJECT_DNA.md`` / ``database/`` / ``outlines/`` /
``chapters/`` / ``reviews/`` / ``memory/`` …). AutoNovel organises the same
artifacts under its own workspace vocabulary (a "bible", a "codex", "beats", a
"manuscript", "critique", "context" …). To **reuse** AutoNovel's chapter-writing
loop instead of building a parallel pipeline (Requirement 7.2), the two layouts
have to be reconciled — every NovelKit artifact must have exactly one AutoNovel
home and vice-versa.

This module is the single source of truth for that mapping. It is a *pure*,
dependency-free path bijection so it is trivially testable and round-trips:

    to_novelkit(to_autonovel(p)) == p     for every NovelKit artifact path p
    to_autonovel(to_novelkit(q)) == q     for every AutoNovel artifact path q

The mapping is prefix-based on the top-level directory (plus a handful of
exact-file rules for the planning docs at the novel root). Top-level names are
disjoint in both directions, so longest-prefix resolution is unambiguous.

Design references: design.md §Architecture "Novel workspace (file-first canon)",
§"Migration Strategy" Phase 5; requirements.md Requirement 7.
"""

from __future__ import annotations

from dataclasses import dataclass


def _norm(rel: str) -> str:
    """Normalise a relative path: strip leading ``./`` and ``/``, use ``/``."""
    rel = str(rel).replace("\\", "/").strip()
    while rel.startswith("./"):
        rel = rel[2:]
    return rel.lstrip("/")


# --------------------------------------------------------------------------- #
# Mapping rules
# --------------------------------------------------------------------------- #

#: Exact-file rules for the root-level planning/canon docs (NovelKit → AutoNovel).
#: These files sit at the novel root in NovelKit; AutoNovel keeps them inside its
#: "bible" so the root stays clean.
_FILE_MAP: dict[str, str] = {
    "PROJECT_DNA.md": "bible/premise.md",
    "PLAN.md": "bible/plan.md",
    "GOAL_TRACKER.md": "bible/goals.md",
}

#: Directory-prefix rules (NovelKit prefix → AutoNovel prefix). Each prefix ends
#: with ``/``. Order is irrelevant — top-level names are disjoint.
_DIR_MAP: tuple[tuple[str, str], ...] = (
    ("database/", "codex/"),       # characters / worldbuilding / systems / …
    ("outlines/", "beats/"),       # master + per-chapter outlines
    ("drafts/", "working/"),       # working artifacts before sync promotion
    ("chapters/", "manuscript/"),  # accepted prose canon
    ("reviews/", "critique/"),     # quality-auditor feedback
    ("memory/", "context/"),       # Memory.md + character snapshots
    ("style_vault/", "voice/"),    # author-style references
    ("logs/", "runtime/"),         # pipeline_status snapshot etc.
    (".commits/", ".commits/"),    # content-addressed sync ledger (kept as-is)
    (".rag/", ".rag/"),            # derivative retrieval index (kept as-is)
)

_FILE_MAP_REV: dict[str, str] = {v: k for k, v in _FILE_MAP.items()}
_DIR_MAP_REV: tuple[tuple[str, str], ...] = tuple((an, nk) for nk, an in _DIR_MAP)

#: Representative artifacts spanning every mapping rule — used by the round-trip
#: property test and as documentation of the canonical novel layout.
CANONICAL_NOVELKIT_ARTIFACTS: tuple[str, ...] = (
    "PROJECT_DNA.md",
    "PLAN.md",
    "GOAL_TRACKER.md",
    "database/characters/protagonist.md",
    "database/worldbuilding/geography.md",
    "database/systems/cultivation.md",
    "database/plot_threads/main.md",
    "database/timeline/events.md",
    "outlines/master_outline.md",
    "outlines/arc_1/chapter_001_outline.md",
    "drafts/chapter_0001.md",
    "drafts/chapter_0001.check.json",
    "chapters/chapter_001.md",
    "reviews/chapter_0001_review.json",
    "reviews/chapter_001_review.md",
    "memory/Memory.md",
    "memory/character_snapshots/chapter_001_character_state.md",
    "style_vault/nhi_can.md",
    "logs/pipeline_status.json",
    ".commits/chapter_0001.commit.json",
    ".rag/index_meta.json",
)


def _apply_prefix_rules(
    rel: str, dir_rules: tuple[tuple[str, str], ...]
) -> str | None:
    for src, dst in dir_rules:
        if rel == src.rstrip("/"):
            return dst.rstrip("/")
        if rel.startswith(src):
            return dst + rel[len(src):]
    return None


def to_autonovel(rel: str) -> str:
    """Map a NovelKit relative artifact path to its AutoNovel path.

    Unrecognised paths pass through unchanged (so the mapping is total).
    """
    rel = _norm(rel)
    if rel in _FILE_MAP:
        return _FILE_MAP[rel]
    mapped = _apply_prefix_rules(rel, _DIR_MAP)
    return mapped if mapped is not None else rel


def to_novelkit(rel: str) -> str:
    """Map an AutoNovel relative artifact path back to its NovelKit path.

    Inverse of :func:`to_autonovel` on every canonical artifact path.
    """
    rel = _norm(rel)
    if rel in _FILE_MAP_REV:
        return _FILE_MAP_REV[rel]
    mapped = _apply_prefix_rules(rel, _DIR_MAP_REV)
    return mapped if mapped is not None else rel


# --------------------------------------------------------------------------- #
# Convenience object
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ArtifactLayoutMap:
    """Object wrapper over the pure mapping functions (ergonomic seam).

    Exposes the same bijection plus a :meth:`describe` table that the surface
    (CLI/docs) can render to show the "old → new" layout map.
    """

    def to_autonovel(self, rel: str) -> str:
        return to_autonovel(rel)

    def to_novelkit(self, rel: str) -> str:
        return to_novelkit(rel)

    def round_trips(self, rel: str) -> bool:
        """True when ``rel`` survives a NovelKit→AutoNovel→NovelKit round-trip."""
        return to_novelkit(to_autonovel(_norm(rel))) == _norm(rel)

    def describe(self) -> list[dict[str, str]]:
        """The full mapping table (NovelKit ↔ AutoNovel), for docs/CLI output."""
        rows = [
            {"novelkit": nk, "autonovel": an, "kind": "file"}
            for nk, an in _FILE_MAP.items()
        ]
        rows += [
            {"novelkit": nk, "autonovel": an, "kind": "dir"}
            for nk, an in _DIR_MAP
        ]
        return rows


#: Module-level singleton for convenience.
LAYOUT = ArtifactLayoutMap()

__all__ = [
    "to_autonovel",
    "to_novelkit",
    "ArtifactLayoutMap",
    "LAYOUT",
    "CANONICAL_NOVELKIT_ARTIFACTS",
]
