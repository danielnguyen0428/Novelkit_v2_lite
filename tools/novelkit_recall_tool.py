"""NovelKit recall tool — 4-dimension related-chapter recommendation (Req 5).

Generic semantic retrieval (the context engine) recalls *facts*; this tool
recalls *which past chapters the writer should re-read* along four
narrative-bookkeeping dimensions, plus a preview of the next chapter so the
writer can design the end-hook / foreshadow handoff. This is the chapter-recall
(voice/texture continuity) that complements fact-recall.

Dimensions (all backed by data NovelKit already keeps):
- ``foreshadow``    — seeds/loops due or orphaned (``novelkit_strand``).
- ``appearance``    — named minor cast last seen (``minor_cast`` memory).
- ``state_change``  — recent character-state updates (``character_state``).
- ``relationship``  — recent relationship shifts (``relationships``).

Pure over (memory, strand, outlines): same inputs ⇒ same output (P17), bounded
to ``k_per_dim`` per dimension. Self-registers as ``novelkit_recall``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from tools import registry
from tools.novelkit_longform_config import load_config

_LOG = logging.getLogger("novelkit.recall")

_GOAL_RE = re.compile(r"##\s*M[uụ]c ti[êe]u.*?\n+(.+)", re.IGNORECASE)
_HOOK_RE = re.compile(r"(?:##\s*Hook|Hook ending|Type:)\s*(.+)", re.IGNORECASE)


def _provider():
    from plugins.memory.novelkit_memory import get_provider

    return get_provider()


def _memory_db_exists(scope: Path) -> bool:
    """True only when the per-novel memory DB already exists. Recall must be a
    pure read (P17) — it must never create the store as a side effect."""
    return (scope / "memory" / "items.sqlite3").exists()


def _memory_dimension(
    scope: Path, category_value: str, dimension: str, chapter: int, k: int
) -> list[dict[str, Any]]:
    if not _memory_db_exists(scope):
        return []
    try:
        items = _provider().store(scope).query(
            category=category_value, status="active", limit=10_000
        )
    except Exception:  # noqa: BLE001 — memory optional; recall must never crash
        _LOG.warning(
            "recall: memory read failed for category %r under %s; skipping dimension",
            category_value, scope, exc_info=True,
        )
        return []
    rows: list[tuple[int, str, str]] = []
    for it in items:
        ch = it.source_chapter
        if category_value == "minor_cast":
            ch = it.payload.get("last_seen") or it.source_chapter
        if not isinstance(ch, int) or ch >= chapter or ch <= 0:
            continue
        rows.append((ch, it.subject, it.value))
    # Deterministic: newest first, then subject; dedupe by chapter.
    rows.sort(key=lambda r: (-r[0], r[1]))
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for ch, subject, value in rows:
        if ch in seen:
            continue
        seen.add(ch)
        out.append(
            {"chapter": ch, "dimension": dimension, "reason": f"{subject}: {value}"[:160]}
        )
        if len(out) >= k:
            break
    return out


def _foreshadow_dimension(scope: Path, chapter: int, k: int) -> list[dict[str, Any]]:
    try:
        from tools.novelkit_strand_tool import weave

        report = weave(scope, chapter)
    except Exception:  # noqa: BLE001 — strand log optional
        _LOG.warning(
            "recall: strand weave failed under %s at chapter %d; "
            "skipping foreshadow dimension", scope, chapter, exc_info=True,
        )
        return []
    candidates: list[tuple[int, str]] = []
    for bucket in ("due_payoffs", "orphan_seeds"):
        for entry in report.get(bucket, []) or []:
            planted = entry.get("chapter_planted")
            if isinstance(planted, int) and 0 < planted < chapter:
                label = entry.get("summary") or entry.get("event_id") or "seed"
                candidates.append((planted, str(label)))
    candidates.sort(key=lambda r: (r[0], r[1]))
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for planted, label in candidates:
        if planted in seen:
            continue
        seen.add(planted)
        out.append(
            {"chapter": planted, "dimension": "foreshadow",
             "reason": f"伏笔/loop: {label}"[:160]}
        )
        if len(out) >= k:
            break
    return out


def _next_chapter_preview(scope: Path, chapter: int) -> Optional[dict[str, Any]]:
    nxt = chapter + 1
    matches = sorted(scope.glob(f"outlines/**/chapter_{nxt:03d}_outline.md"))
    if not matches:
        return None
    try:
        text = matches[0].read_text(encoding="utf-8")
    except OSError:
        # Recall is a pure read that must never crash (P17); an unreadable
        # outline yields no preview rather than propagating the error, matching
        # every other best-effort read in this module.
        _LOG.warning(
            "recall: could not read next-chapter outline %s; skipping preview",
            matches[0], exc_info=True,
        )
        return None
    goal = _GOAL_RE.search(text)
    hook = _HOOK_RE.search(text)
    return {
        "chapter": nxt,
        "goal": (goal.group(1).strip() if goal else "")[:240],
        "hook": (hook.group(1).strip() if hook else "")[:160],
        "path": matches[0].relative_to(scope).as_posix(),
    }


def recommend_chapters(
    novel_path: str | Path, chapter: int, *, k_per_dim: Optional[int] = None
) -> dict[str, Any]:
    """Recommend related chapters across four dimensions + next-chapter preview.

    Pure over (memory, strand, outlines); bounded to ``k_per_dim`` per
    dimension (defaults from ``config/longform.json``). Returns an empty
    ``related_chapters`` for the first chapter / a novel with no history (P17).
    """
    scope = Path(novel_path)
    if k_per_dim is None:
        k_per_dim = int(load_config(scope).get("K_PER_DIM", 2))
    related: list[dict[str, Any]] = []
    related += _foreshadow_dimension(scope, chapter, k_per_dim)
    related += _memory_dimension(scope, "minor_cast", "appearance", chapter, k_per_dim)
    related += _memory_dimension(scope, "character_state", "state_change", chapter, k_per_dim)
    related += _memory_dimension(scope, "relationships", "relationship", chapter, k_per_dim)
    return {
        "chapter": chapter,
        "related_chapters": related,
        "next_chapter_preview": _next_chapter_preview(scope, chapter),
    }


def assemble_writer_context(
    novel_path: str | Path, chapter: int, *, k_per_dim: Optional[int] = None
) -> dict[str, Any]:
    """Bundle the long-form additions injected into the Prose Writer envelope
    for ``chapter`` (Req 5.4, 6.4, 7.2): related chapters + next-chapter preview
    + recent named cast + the writer's own style-stats self-mirror.

    Behind feature flags (``recall`` / ``minor_cast`` / ``style_stats``): a
    disabled flag yields an empty slice, so a flags-off deployment injects
    nothing (rollback-safe). Pure read over memory/strand/outlines/logs.
    """
    import json as _json

    scope = Path(novel_path)
    cfg = load_config(scope)
    flags = cfg.get("flags", {})
    out: dict[str, Any] = {
        "related_chapters": [],
        "next_chapter_preview": None,
        "recent_cast": [],
        "style_stats": None,
        "style_exemplars": None,
        "style_edits": None,
        "global_craft": None,
    }
    if flags.get("recall", False):
        recall = recommend_chapters(scope, chapter, k_per_dim=k_per_dim)
        out["related_chapters"] = recall["related_chapters"]
        out["next_chapter_preview"] = recall["next_chapter_preview"]
    if flags.get("minor_cast", False) and _memory_db_exists(scope):
        try:
            from plugins.memory.novelkit_memory import recent_cast

            limit = int(cfg.get("RECENT_CAST_LIMIT", 12))
            out["recent_cast"] = [
                {"name": i.subject, **i.payload}
                for i in recent_cast(scope, limit=limit)
            ]
        except Exception:  # noqa: BLE001 — memory optional
            _LOG.warning(
                "recall: recent_cast read failed under %s; omitting cast slice",
                scope, exc_info=True,
            )
    if flags.get("style_stats", False):
        stats_path = scope / "logs" / "style_stats.json"
        if stats_path.exists():
            try:
                out["style_stats"] = _json.loads(stats_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        exemplars_path = scope / "logs" / "style_exemplars.json"
        if exemplars_path.exists():
            try:
                out["style_exemplars"] = _json.loads(
                    exemplars_path.read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                pass
    if flags.get("style_edits", False):
        edits_path = scope / "logs" / "style_edits.json"
        if edits_path.exists():
            try:
                out["style_edits"] = _json.loads(edits_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
    if flags.get("style_global", False):
        try:
            from tools.novelkit_style_coherence_tool import load_global_craft_metrics

            out["global_craft"] = load_global_craft_metrics()
        except Exception:  # noqa: BLE001 — global profile optional/best-effort
            pass
    return out


def recall_tool(action: str, **kwargs: Any) -> Any:
    if action == "recommend_chapters":
        return recommend_chapters(**kwargs)
    if action == "assemble_writer_context":
        return assemble_writer_context(**kwargs)
    raise ValueError(
        f"unknown action {action!r}; expected recommend_chapters|assemble_writer_context"
    )


registry.register(
    "novelkit_recall",
    recall_tool,
    schema={
        "name": "novelkit_recall",
        "description": "4-dimension related-chapter recall + next-chapter preview.",
        "input": {
            "type": "object",
            "properties": {
                "action": {"type": "string",
                           "enum": ["recommend_chapters", "assemble_writer_context"]},
                "novel_path": {"type": "string"},
                "chapter": {"type": "integer"},
                "k_per_dim": {"type": "integer"},
            },
            "required": ["action", "novel_path", "chapter"],
        },
        "output": {"type": "object"},
    },
    module=__name__,
)


__all__ = ["recall_tool", "recommend_chapters", "assemble_writer_context"]
