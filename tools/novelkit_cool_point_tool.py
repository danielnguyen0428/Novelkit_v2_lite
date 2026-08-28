"""NovelKit cool-point tool — 4-layer 爽点 (cool point) structure detection.

Phase 3 of the migration (Task 9.1). Extracts the cool-point analysis
algorithm from the legacy ``cool_point_analyzer.py`` and repackages it as a
self-registering Hermes Custom Tool. A *cool point* is a payoff scene — the bit
serial readers screenshot and share — and the analyzer claims those scenes only
land when they are built from four layers that arrive in order:

1. **setup**      — tension / buildup.
2. **release**    — the decisive action (strike, verdict, reveal).
3. **reaction**   — observers register the moment across widening tiers
                    (1 = protagonist, 2 = nearby, 3 = distant audience).
4. **transition** — aftermath / pivot to the next question.

Marker phrases live in ``config/cool_point_markers.json`` so authors can tune
detection without touching code. The module is dependency-free (stdlib only)
plus the local ``tools.registry`` shim, so it is verifiable in isolation.

Design references: design.md §"Components and Interfaces" #5
(``analyze(chapter, genre) -> {cool_points[], density, gaps[]}``).
Requirements 15/16 (prose quality / pacing).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from tools import registry

logger = logging.getLogger(__name__)

#: Config filename (ported from cp_constants.COOL_POINT_CONFIG_FILENAME).
COOL_POINT_CONFIG_FILENAME = "cool_point_markers.json"

#: Default config path — ``novelkit-hermes/config/cool_point_markers.json``.
DEFAULT_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[1] / "config" / COOL_POINT_CONFIG_FILENAME
)

#: Canonical layer names, in narrative order.
LAYERS: tuple[str, ...] = ("setup", "release", "reaction", "transition")

#: How many consecutive unclassified paragraphs close a growing block.
_MAX_CONNECTOR_NONES: int = 1


# Reaction-tier markers (ported verbatim from cool_point_analyzer.py).
_TIER2_MARKERS: tuple[str, ...] = (
    "mọi người", "mọi nguoi", "đồng đạo", "đồng môn", "huynh đệ",
    "đám đệ tử", "đám người", "xung quanh", "có người", "ai đó",
    "tiếng xôn xao", "có kẻ thì thầm", "nhóm người", "người bên cạnh",
)
_TIER3_MARKERS: tuple[str, ...] = (
    "cả thành", "toàn thành", "khắp đại lục", "thiên hạ",
    "tin tức lan", "lan truyền", "cả tông môn", "toàn bộ tông môn",
    "vạn người", "cả gia tộc", "tin đồn", "khắp nơi",
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CoolPointBlock:
    """One detected cool-point block, decomposed into 4 layers."""

    chapter: int
    block_index: int
    setup_text: str
    setup_words: int
    release_text: str
    release_words: int
    reaction_text: str
    reaction_words: int
    reaction_tier_count: int
    transition_text: str
    transition_words: int
    pacing_ratio: float
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoolPointReport:
    """Chapter-level cool-point report."""

    chapter: int
    blocks: list[CoolPointBlock] = field(default_factory=list)
    avg_pacing_ratio: float = 0.0
    avg_reaction_tiers: float = 0.0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _load_markers_cached(path_str: str) -> dict[str, tuple[str, ...]]:
    """Load and validate ``cool_point_markers.json`` (cached by path).

    A missing / unreadable / malformed config yields a dict with every layer
    mapped to an empty tuple — bad config can never crash the gate.
    """
    path = Path(path_str)
    if not path.exists():
        logger.warning("cool_point: config not found at %s", path)
        return {layer: () for layer in LAYERS}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("cool_point: failed to read %s: %s", path, exc)
        return {layer: () for layer in LAYERS}
    if not isinstance(raw, dict):
        logger.warning("cool_point: config root must be an object")
        return {layer: () for layer in LAYERS}

    cleaned: dict[str, tuple[str, ...]] = {}
    for layer in LAYERS:
        markers = raw.get(layer, [])
        if not isinstance(markers, list):
            cleaned[layer] = ()
            continue
        seen: set[str] = set()
        out: list[str] = []
        for entry in markers:
            if not isinstance(entry, str):
                continue
            lowered = entry.strip().lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            out.append(lowered)
        cleaned[layer] = tuple(out)
    return cleaned


def load_cool_point_markers(
    path: Optional[Path] = None,
) -> dict[str, tuple[str, ...]]:
    """Load cool-point marker tuples keyed by layer name."""
    target = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    return _load_markers_cached(str(target))


def _clear_marker_cache() -> None:
    """Test helper — drop the cached config so callers can swap files."""
    _load_markers_cached.cache_clear()


# ---------------------------------------------------------------------------
# Classification helpers (ported from cool_point_analyzer.py)
# ---------------------------------------------------------------------------


def _count_marker_hits(text_lower: str, markers: tuple[str, ...]) -> int:
    """Total marker matches in ``text_lower`` (Unicode-aware word boundaries)."""
    if not text_lower or not markers:
        return 0
    total = 0
    for marker in markers:
        if not marker:
            continue
        try:
            pattern = re.compile(
                r"(?<!\w)" + re.escape(marker) + r"(?!\w)",
                flags=re.IGNORECASE | re.UNICODE,
            )
        except re.error:
            continue
        total += len(pattern.findall(text_lower))
    return total


def _count_reaction_tiers(reaction_text: str) -> int:
    """Count present reaction tiers in 0..3 (0 == no reaction layer)."""
    if not reaction_text or not reaction_text.strip():
        return 0
    text_lower = reaction_text.lower()
    tier_count = 1
    if _count_marker_hits(text_lower, _TIER2_MARKERS) > 0:
        tier_count = max(tier_count, 2)
    if _count_marker_hits(text_lower, _TIER3_MARKERS) > 0:
        tier_count = max(tier_count, 3)
    return max(0, min(3, tier_count))


def classify_paragraph(paragraph: str) -> tuple[Optional[str], dict[str, int]]:
    """Classify a paragraph into one of the 4 cool-point layers.

    Returns ``(layer_name, scores_dict)``; ties break by :data:`LAYERS` order
    so a paragraph straddling two layers leans toward the earlier beat.
    """
    zero_scores = {layer: 0 for layer in LAYERS}
    if not paragraph or not paragraph.strip():
        return None, zero_scores

    markers_by_layer = load_cool_point_markers()
    text_lower = paragraph.lower()
    scores: dict[str, int] = {
        layer: _count_marker_hits(text_lower, markers_by_layer.get(layer, ()))
        for layer in LAYERS
    }
    if all(score == 0 for score in scores.values()):
        return None, scores

    best_layer = LAYERS[0]
    best_score = scores[best_layer]
    for layer in LAYERS[1:]:
        if scores[layer] > best_score:
            best_layer = layer
            best_score = scores[layer]
    return best_layer, scores


# ---------------------------------------------------------------------------
# Block clustering (ported from cool_point_analyzer.py)
# ---------------------------------------------------------------------------


def _split_paragraphs(chapter_text: str) -> list[str]:
    if not chapter_text:
        return []
    return [chunk.strip() for chunk in chapter_text.split("\n\n") if chunk.strip()]


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _cluster_blocks(
    classifications: list[tuple[str, Optional[str]]],
) -> list[list[tuple[str, Optional[str]]]]:
    """Group ``(paragraph, layer)`` rows into cool-point blocks."""
    blocks: list[list[tuple[str, Optional[str]]]] = []
    current: list[tuple[str, Optional[str]]] = []
    none_streak = 0

    for paragraph, layer in classifications:
        if layer is not None:
            current.append((paragraph, layer))
            none_streak = 0
            continue
        if not current:
            continue
        none_streak += 1
        if none_streak > _MAX_CONNECTOR_NONES:
            while current and current[-1][1] is None:
                current.pop()
            if current:
                blocks.append(current)
            current = []
            none_streak = 0
        else:
            current.append((paragraph, None))

    while current and current[-1][1] is None:
        current.pop()
    if current:
        blocks.append(current)
    return blocks


def _join_layer(rows: list[tuple[str, Optional[str]]], layer: str) -> str:
    parts = [paragraph for paragraph, row_layer in rows if row_layer == layer]
    return "\n\n".join(parts)


def _build_block(
    chapter: int, block_index: int, rows: list[tuple[str, Optional[str]]]
) -> CoolPointBlock:
    setup_text = _join_layer(rows, "setup")
    release_text = _join_layer(rows, "release")
    reaction_text = _join_layer(rows, "reaction")
    transition_text = _join_layer(rows, "transition")
    setup_words = _word_count(setup_text)
    release_words = _word_count(release_text)
    return CoolPointBlock(
        chapter=int(chapter),
        block_index=int(block_index),
        setup_text=setup_text,
        setup_words=setup_words,
        release_text=release_text,
        release_words=release_words,
        reaction_text=reaction_text,
        reaction_words=_word_count(reaction_text),
        reaction_tier_count=_count_reaction_tiers(reaction_text),
        transition_text=transition_text,
        transition_words=_word_count(transition_text),
        pacing_ratio=float(setup_words / max(1, release_words)),
        issues=[],
    )


# ---------------------------------------------------------------------------
# Public detection entry point
# ---------------------------------------------------------------------------


def detect_cool_points(chapter_text: str, chapter: int) -> CoolPointReport:
    """Detect cool-point blocks in a chapter and decompose each into 4 layers.

    A chapter without any release-layer paragraph simply has no cool point in
    it (set-up chapters are like that), which is reported as empty ``blocks``.
    """
    chapter_int = int(chapter)
    paragraphs = _split_paragraphs(chapter_text)
    if not paragraphs:
        return CoolPointReport(chapter=chapter_int)

    classifications: list[tuple[str, Optional[str]]] = []
    for paragraph in paragraphs:
        layer, _scores = classify_paragraph(paragraph)
        classifications.append((paragraph, layer))

    raw_blocks = _cluster_blocks(classifications)
    retained_rows = [
        rows for rows in raw_blocks if any(layer == "release" for _, layer in rows)
    ]
    blocks = [
        _build_block(chapter_int, idx, rows)
        for idx, rows in enumerate(retained_rows)
    ]

    if blocks:
        avg_pacing_ratio = sum(b.pacing_ratio for b in blocks) / len(blocks)
        avg_reaction_tiers = sum(b.reaction_tier_count for b in blocks) / len(blocks)
    else:
        avg_pacing_ratio = 0.0
        avg_reaction_tiers = 0.0

    return CoolPointReport(
        chapter=chapter_int,
        blocks=blocks,
        avg_pacing_ratio=float(avg_pacing_ratio),
        avg_reaction_tiers=float(avg_reaction_tiers),
        issues=[],
    )


def _gaps_for(blocks: list[CoolPointBlock]) -> list[dict[str, Any]]:
    """Describe per-block structural gaps (missing layers / thin reaction)."""
    gaps: list[dict[str, Any]] = []
    for block in blocks:
        missing = [
            layer
            for layer in LAYERS
            if _word_count(getattr(block, f"{layer}_text")) == 0
        ]
        if missing or block.reaction_tier_count < 2:
            gaps.append(
                {
                    "block_index": block.block_index,
                    "missing_layers": missing,
                    "reaction_tier_count": block.reaction_tier_count,
                }
            )
    return gaps


def analyze(
    chapter_text: str, chapter: int, genre: Optional[str] = None
) -> dict[str, Any]:
    """Tool interface (design #5): ``analyze -> {cool_points, density, gaps}``.

    ``genre`` is accepted for API parity (markers are global config today) and
    echoed back. ``density`` is cool points per 1000 words of chapter prose.
    """
    report = detect_cool_points(chapter_text, chapter)
    total_words = _word_count(chapter_text)
    density = round(len(report.blocks) / (total_words / 1000.0), 4) if total_words else 0.0
    return {
        "chapter": report.chapter,
        "genre": genre,
        "cool_points": [b.to_dict() for b in report.blocks],
        "count": len(report.blocks),
        "density": density,
        "avg_pacing_ratio": report.avg_pacing_ratio,
        "avg_reaction_tiers": report.avg_reaction_tiers,
        "gaps": _gaps_for(report.blocks),
    }


# ---------------------------------------------------------------------------
# Tool entrypoint + self-registration (Requirement 6.2)
# ---------------------------------------------------------------------------

_COOL_POINT_TOOL_SCHEMA = {
    "name": "novelkit_cool_point",
    "description": (
        "Cool-point (爽点) analyzer: detect 4-layer payoff blocks "
        "(setup → release → reaction → transition), pacing ratio, reaction "
        "tier spread, density per 1000 words, and structural gaps."
    ),
    "input": {
        "type": "object",
        "properties": {
            "chapter_text": {"type": "string"},
            "chapter": {"type": "integer"},
            "genre": {"type": ["string", "null"]},
        },
        "required": ["chapter_text", "chapter"],
    },
    "output": {"type": "object"},
}


def cool_point_tool(
    chapter_text: str, chapter: int, *, genre: Optional[str] = None
) -> dict[str, Any]:
    """Stateless tool entrypoint — wraps :func:`analyze`."""
    return analyze(chapter_text, chapter, genre)


registry.register(
    "novelkit_cool_point",
    cool_point_tool,
    schema=_COOL_POINT_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "LAYERS",
    "CoolPointBlock",
    "CoolPointReport",
    "load_cool_point_markers",
    "classify_paragraph",
    "detect_cool_points",
    "analyze",
    "cool_point_tool",
]
