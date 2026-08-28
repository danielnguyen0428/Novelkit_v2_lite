"""NovelKit strand tool — strand pacing + open-loop / foreshadowing tracking.

Phase 3 of the migration (Task 9.2). Merges three legacy modules into one
self-registering Hermes Custom Tool (resolving the strand/loop sprawl):

- ``strand_weaver.py`` — classify each chapter into a dominant *strand*
  (Quest / Fire / Constellation) and compute rolling-window pacing metrics.
- ``open_loops.py`` — event-driven open-loop tracking (seed → thread → payoff)
  with urgency, deadlines and append-only event log.
- ``migrate_plot_threads_to_loops.py`` — one-shot migration of legacy
  ``database/plot_threads/*.md`` markdown into the open-loop event log.

Keyword tables live in ``config/strand_keywords.json`` so authors can tune
detection without code changes. The module is dependency-free (stdlib only)
plus the local ``tools.registry`` shim.

Design references: design.md §"Components and Interfaces" #6
(``weave(plot_threads, chapter) -> {open_loops[], due_payoffs[], orphan_seeds[]}``).
Requirements 11/17/18 (sync foreshadowing, hybrid pacing, long-form coherence).
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from tools import registry

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constants (ported from cp_constants.py — kept identical)
# --------------------------------------------------------------------------- #

#: Strand pacing knobs.
STRAND_QUEST_MAX_STREAK = 5
STRAND_FIRE_MAX_GAP = 10
STRAND_CONSTELLATION_MAX_GAP = 15
STRAND_PACING_LOOKBACK = 20

STRAND_QUEST = "quest"
STRAND_FIRE = "fire"
STRAND_CONSTELLATION = "constellation"
STRAND_VALUES: tuple[str, ...] = (STRAND_QUEST, STRAND_FIRE, STRAND_CONSTELLATION)
STRAND_TARGET_DISTRIBUTION: dict[str, float] = {
    STRAND_QUEST: 0.60,
    STRAND_FIRE: 0.20,
    STRAND_CONSTELLATION: 0.20,
}

STRAND_CONFIG_FILENAME = "strand_keywords.json"
STRAND_METADATA_FILENAME = ".strands.json"

#: Open-loop knobs.
LOOP_DEBT_MAX_DEFAULT = 8
LOOP_URGENT_TOP_N = 3
LOOP_DEADLINE_IMMINENT_WINDOW = 5
LOOP_EVENT_LOG_FILENAME = "open_loops.jsonl"

#: Default config path — ``novelkit-hermes/config/strand_keywords.json``.
DEFAULT_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[1] / "config" / STRAND_CONFIG_FILENAME
)


# --------------------------------------------------------------------------- #
# Strand enums + dataclasses
# --------------------------------------------------------------------------- #


class Strand(str, Enum):
    QUEST = STRAND_QUEST
    FIRE = STRAND_FIRE
    CONSTELLATION = STRAND_CONSTELLATION


_TIEBREAK_ORDER: tuple[str, ...] = (
    Strand.QUEST.value,
    Strand.FIRE.value,
    Strand.CONSTELLATION.value,
)


@dataclass
class ChapterStrand:
    chapter: int
    dominant_strand: str
    strand_scores: dict[str, int] = field(default_factory=dict)
    weight: float = 0.5
    explicit: bool = False

    def to_dict(self, *, include_timestamp: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "strand": self.dominant_strand,
            "weight": float(self.weight),
            "explicit": bool(self.explicit),
        }
        if include_timestamp:
            payload["detected_at"] = datetime.now(UTC).isoformat()
        return payload


@dataclass
class PacingReport:
    current_chapter: int
    last_n_chapters: int
    chapters_considered: int
    strand_distribution: dict[str, float] = field(default_factory=dict)
    target_distribution: dict[str, float] = field(default_factory=dict)
    quest_streak: int = 0
    fire_gap: int = 0
    constellation_gap: int = 0
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Strand config loading
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=8)
def _load_keywords_cached(path_str: str) -> dict[str, tuple[str, ...]]:
    """Load and validate strand_keywords.json (cached). Bad config → empty."""
    path = Path(path_str)
    if not path.exists():
        logger.warning("strand: config not found at %s", path)
        return {strand: () for strand in STRAND_VALUES}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("strand: failed to read %s: %s", path, exc)
        return {strand: () for strand in STRAND_VALUES}
    if not isinstance(raw, dict):
        return {strand: () for strand in STRAND_VALUES}
    section = raw.get("strands") if isinstance(raw.get("strands"), dict) else raw

    cleaned: dict[str, tuple[str, ...]] = {}
    for strand in STRAND_VALUES:
        keywords = section.get(strand, []) if isinstance(section, dict) else []
        if not isinstance(keywords, list):
            cleaned[strand] = ()
            continue
        seen: set[str] = set()
        out: list[str] = []
        for entry in keywords:
            if not isinstance(entry, str):
                continue
            lowered = entry.strip().lower()
            if not lowered or lowered in seen:
                continue
            seen.add(lowered)
            out.append(lowered)
        cleaned[strand] = tuple(out)
    return cleaned


def load_strand_keywords(path: Optional[Path] = None) -> dict[str, tuple[str, ...]]:
    target = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    return _load_keywords_cached(str(target))


def _clear_keyword_cache() -> None:
    """Test helper — drop the cached config so callers can swap files."""
    _load_keywords_cached.cache_clear()


# --------------------------------------------------------------------------- #
# Strand detection helpers
# --------------------------------------------------------------------------- #

_VALID_STRAND_VALUES: frozenset[str] = frozenset(STRAND_VALUES)


def _coerce_explicit_strand(raw: Any) -> Optional[str]:
    if raw is None or isinstance(raw, bool):
        return None
    text = str(raw).strip().lower()
    return text if text in _VALID_STRAND_VALUES else None


def _count_keyword_hits(text_lower: str, keywords: tuple[str, ...]) -> int:
    """Total keyword matches in ``text_lower`` (Unicode-aware word boundaries)."""
    if not text_lower or not keywords:
        return 0
    total = 0
    for keyword in keywords:
        if not keyword:
            continue
        try:
            pattern = re.compile(
                r"(?<!\w)" + re.escape(keyword) + r"(?!\w)",
                flags=re.IGNORECASE | re.UNICODE,
            )
        except re.error:
            continue
        total += len(pattern.findall(text_lower))
    return total


def _confidence_from_scores(scores: dict[str, int], dominant: str) -> float:
    """Confidence in [0.5, 1.0] from raw keyword counts."""
    total = sum(int(s) for s in scores.values())
    if total <= 0:
        return 0.5
    dominant_share = scores.get(dominant, 0) / total
    if dominant_share <= 1 / 3:
        return 0.5
    if dominant_share >= 1.0:
        return 1.0
    span = 1.0 - (1 / 3)
    fraction = (dominant_share - 1 / 3) / span
    return round(0.5 + 0.5 * fraction, 4)


def detect_strand(
    chapter_text: str,
    chapter: int,
    frontmatter: Optional[dict[str, Any]] = None,
) -> ChapterStrand:
    """Classify a chapter into its dominant strand (explicit override wins)."""
    keywords = load_strand_keywords()
    explicit_value: Optional[str] = None
    if isinstance(frontmatter, dict):
        candidate = _coerce_explicit_strand(frontmatter.get("strand"))
        if candidate is None and frontmatter.get("strand") is not None:
            logger.warning(
                "strand: ignoring invalid explicit strand %r for chapter %s",
                frontmatter.get("strand"), chapter,
            )
        explicit_value = candidate

    text_lower = (chapter_text or "").lower()
    scores: dict[str, int] = {
        strand: _count_keyword_hits(text_lower, keywords.get(strand, ()))
        for strand in STRAND_VALUES
    }

    if explicit_value is not None:
        return ChapterStrand(
            chapter=chapter,
            dominant_strand=explicit_value,
            strand_scores=scores,
            weight=1.0,
            explicit=True,
        )

    dominant = _TIEBREAK_ORDER[0]
    best_score = -1
    for strand in _TIEBREAK_ORDER:
        score = scores.get(strand, 0)
        if score > best_score:
            best_score = score
            dominant = strand

    return ChapterStrand(
        chapter=chapter,
        dominant_strand=dominant,
        strand_scores=scores,
        weight=_confidence_from_scores(scores, dominant),
        explicit=False,
    )


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", flags=re.DOTALL)


def parse_frontmatter(chapter_text: str) -> tuple[dict[str, Any], str]:
    """Parse a minimal ``key: value`` frontmatter block from a chapter file."""
    if not chapter_text:
        return {}, chapter_text or ""
    match = _FRONTMATTER_RE.match(chapter_text)
    if not match:
        return {}, chapter_text
    block = match.group(1)
    body = chapter_text[match.end():]
    metadata: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            metadata[key] = value
    return metadata, body


# --------------------------------------------------------------------------- #
# Strand storage + pacing report
# --------------------------------------------------------------------------- #


def _strand_metadata_path(novel_path: Path) -> Path:
    return Path(novel_path) / "chapters" / STRAND_METADATA_FILENAME


def _chapter_key(chapter: int) -> str:
    return f"{int(chapter):04d}"


def load_strand_metadata(novel_path: Path) -> dict[str, dict[str, Any]]:
    path = _strand_metadata_path(novel_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("strand: failed to read %s: %s", path, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): dict(value)
        for key, value in payload.items()
        if isinstance(value, dict)
    }


def write_strand_metadata(
    novel_path: Path, chapter_key: str, payload: dict[str, Any]
) -> None:
    path = _strand_metadata_path(novel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_strand_metadata(novel_path)
    existing[chapter_key] = payload
    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def record_chapter_strand(novel_path: Path, strand: ChapterStrand) -> Path:
    write_strand_metadata(novel_path, _chapter_key(strand.chapter), strand.to_dict())
    return _strand_metadata_path(novel_path)


def read_chapter_strand(novel_path: Path, chapter: int) -> Optional[dict[str, Any]]:
    return load_strand_metadata(novel_path).get(_chapter_key(chapter))


def _key_to_int(key: str) -> int:
    try:
        return int(key)
    except (TypeError, ValueError):
        return -1


def _ordered_strand_records(
    metadata: dict[str, dict[str, Any]], current_chapter: int
) -> list[tuple[int, str]]:
    pairs: list[tuple[int, str]] = []
    for key, entry in metadata.items():
        chapter_num = _key_to_int(key)
        if chapter_num < 1:
            continue
        if current_chapter > 0 and chapter_num > current_chapter:
            continue
        strand_value = entry.get("strand")
        if strand_value not in _VALID_STRAND_VALUES:
            continue
        pairs.append((chapter_num, str(strand_value)))
    pairs.sort(key=lambda item: item[0])
    return pairs


def _quest_streak(records: list[tuple[int, str]]) -> int:
    streak = 0
    for _, strand in reversed(records):
        if strand == Strand.QUEST.value:
            streak += 1
        else:
            break
    return streak


def _gap_since_strand(
    records: list[tuple[int, str]], target_strand: str, current_chapter: int
) -> int:
    if not records:
        return max(current_chapter, 0)
    last_hit = 0
    for ch_num, strand in records:
        if strand == target_strand:
            last_hit = ch_num
    if last_hit == 0:
        return max(current_chapter, 0)
    return max(current_chapter - last_hit, 0)


def _distribution(records: list[tuple[int, str]]) -> dict[str, float]:
    if not records:
        return {strand: 0.0 for strand in STRAND_VALUES}
    total = len(records)
    counts: dict[str, int] = {strand: 0 for strand in STRAND_VALUES}
    for _, strand in records:
        counts[strand] = counts.get(strand, 0) + 1
    return {s: round(counts.get(s, 0) / total, 4) for s in STRAND_VALUES}


def pacing_report(
    novel_path: Path, current_chapter: int, lookback: int = STRAND_PACING_LOOKBACK
) -> PacingReport:
    """Compute the rolling-window pacing report."""
    if lookback <= 0:
        lookback = 1
    metadata = load_strand_metadata(novel_path)
    records_full = _ordered_strand_records(metadata, current_chapter)
    records_window = records_full[-lookback:] if records_full else []

    quest_streak = _quest_streak(records_full)
    fire_gap = _gap_since_strand(records_full, Strand.FIRE.value, current_chapter)
    constellation_gap = _gap_since_strand(
        records_full, Strand.CONSTELLATION.value, current_chapter
    )

    issues: list[str] = []
    if quest_streak >= STRAND_QUEST_MAX_STREAK + 1:
        issues.append("PACING_QUEST_OVERLOAD")
    if fire_gap >= STRAND_FIRE_MAX_GAP + 1:
        issues.append("PACING_FIRE_DROUGHT")
    if constellation_gap >= STRAND_CONSTELLATION_MAX_GAP + 1:
        issues.append("PACING_WORLDBUILDING_DROUGHT")

    return PacingReport(
        current_chapter=int(current_chapter),
        last_n_chapters=int(lookback),
        chapters_considered=len(records_window),
        strand_distribution=_distribution(records_window),
        target_distribution=dict(STRAND_TARGET_DISTRIBUTION),
        quest_streak=quest_streak,
        fire_gap=fire_gap,
        constellation_gap=constellation_gap,
        issues=issues,
    )


# --------------------------------------------------------------------------- #
# Open-loop tracking (ported from open_loops.py)
# --------------------------------------------------------------------------- #


class LoopType(str, Enum):
    VOW = "vow"
    MYSTERY = "mystery"
    THREAT = "threat"
    INHERITANCE = "inheritance"
    DEBT = "debt"
    CURSE = "curse"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_URGENCY_RANK: dict[str, int] = {
    Urgency.LOW.value: 0,
    Urgency.MEDIUM.value: 1,
    Urgency.HIGH.value: 2,
    Urgency.CRITICAL.value: 3,
}


@dataclass
class OpenLoopEvent:
    event_id: str
    event_type: str
    subject: str
    chapter_planted: int
    content: str = ""
    loop_type: str = "mystery"
    urgency: str = "medium"
    expected_payoff: Optional[int] = None
    loop_deadline: Optional[int] = None
    chapter_closed: Optional[int] = None
    resolution: Optional[str] = None
    closed_by_event: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReaderPullData:
    urgent_loops: list[OpenLoopEvent] = field(default_factory=list)
    deadline_imminent: list[OpenLoopEvent] = field(default_factory=list)
    debt_count: int = 0
    debt_overdue: list[OpenLoopEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "urgent_loops": [e.to_dict() for e in self.urgent_loops],
            "deadline_imminent": [e.to_dict() for e in self.deadline_imminent],
            "debt_count": int(self.debt_count),
            "debt_overdue": [e.to_dict() for e in self.debt_overdue],
        }


def _event_log_path(novel_path: Path) -> Path:
    return Path(novel_path) / "database" / LOOP_EVENT_LOG_FILENAME


_OUTLINE_LOOP_MARKERS: tuple[tuple[str, str], ...] = (
    ("đính ước", LoopType.VOW.value),
    ("hứa", LoopType.VOW.value),
    ("thề", LoopType.VOW.value),
    ("không biết tại sao", LoopType.MYSTERY.value),
    ("câu hỏi", LoopType.MYSTERY.value),
    ("bí ẩn", LoopType.MYSTERY.value),
    ("bí mật", LoopType.MYSTERY.value),
    ("tai họa sắp", LoopType.THREAT.value),
    ("mối đe dọa", LoopType.THREAT.value),
    ("đại nạn", LoopType.THREAT.value),
    ("kẻ thù", LoopType.THREAT.value),
    ("huyết mạch", LoopType.INHERITANCE.value),
    ("thân thế", LoopType.INHERITANCE.value),
    ("kế thừa", LoopType.INHERITANCE.value),
    ("di sản", LoopType.INHERITANCE.value),
    ("ơn nghĩa", LoopType.DEBT.value),
    ("phải trả", LoopType.DEBT.value),
    ("nợ", LoopType.DEBT.value),
    ("lời nguyền", LoopType.CURSE.value),
    ("ấn ký", LoopType.CURSE.value),
    ("phong ấn", LoopType.CURSE.value),
)

_PAYOFF_MIN_TOKEN_LEN = 5

_PAYOFF_STOP_WORDS: frozenset[str] = frozenset(
    {
        "detected", "payoff", "loop", "with", "that", "this", "from", "into",
        "have", "been", "were", "their", "there", "would", "could", "should",
        "không", "được", "những", "cũng", "trong", "nhưng", "người", "chưa",
        "đang", "nhiều", "phải", "thật", "đều", "rằng", "mình", "chính",
        "thấy", "biết", "muốn", "theo", "trước", "thành", "thăng", "thì",
        "đây", "khi", "còn", "lại", "nên", "bởi", "vì",
    }
)


def _strip_diacritics(text: str) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d").replace("Đ", "D")


def _slugify(text: str) -> str:
    if not text:
        return ""
    ascii_form = _strip_diacritics(text).lower()
    return re.sub(r"[^a-z0-9]+", "_", ascii_form).strip("_")


def _excerpt_around(text: str, position: int, length: int = 100) -> str:
    if not text:
        return ""
    half = max(length // 2, 0)
    start = max(position - half, 0)
    end = min(start + length, len(text))
    start = max(end - length, 0)
    return text[start:end].strip()


def _event_from_dict(payload: dict[str, Any]) -> OpenLoopEvent:
    def _opt_int(key: str) -> Optional[int]:
        return int(payload[key]) if payload.get(key) is not None else None

    return OpenLoopEvent(
        event_id=str(payload["event_id"]),
        event_type=str(payload["event_type"]),
        subject=str(payload.get("subject", "")),
        chapter_planted=int(payload["chapter_planted"]),
        content=str(payload.get("content", "")),
        loop_type=str(payload.get("loop_type", LoopType.MYSTERY.value)),
        urgency=str(payload.get("urgency", Urgency.MEDIUM.value)),
        expected_payoff=_opt_int("expected_payoff"),
        loop_deadline=_opt_int("loop_deadline"),
        chapter_closed=_opt_int("chapter_closed"),
        resolution=(
            str(payload["resolution"]) if payload.get("resolution") is not None else None
        ),
        closed_by_event=(
            str(payload["closed_by_event"])
            if payload.get("closed_by_event") is not None
            else None
        ),
        created_at=str(payload.get("created_at", "")),
    )


def _word_boundary_match(keyword: str, text: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, text, flags=re.UNICODE) is not None


def _payoff_keywords_for(loop: OpenLoopEvent) -> list[str]:
    keywords: set[str] = set()
    subject = (loop.subject or "").strip().lower()
    if subject:
        keywords.add(subject)
        spaced = subject.replace("_", " ").strip()
        if spaced and spaced != subject:
            keywords.add(spaced)
    content_lower = (loop.content or "").lower()
    for token in re.findall(r"\w+", content_lower, flags=re.UNICODE):
        if len(token) < _PAYOFF_MIN_TOKEN_LEN or token in _PAYOFF_STOP_WORDS:
            continue
        keywords.add(token)
    return [kw for kw in keywords if kw]


def record_loop_event(novel_path: Path, event: OpenLoopEvent) -> None:
    """Append ``event`` to ``database/open_loops.jsonl`` (append-only)."""
    if not event.created_at:
        event.created_at = datetime.now(UTC).isoformat()
    path = _event_log_path(novel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def get_active_loops(novel_path: Path) -> list[OpenLoopEvent]:
    """Return loops created but not yet closed (sorted by chapter_planted)."""
    path = _event_log_path(novel_path)
    if not path.exists():
        return []
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        logger.warning("strand/open_loops: failed to read %s: %s", path, exc)
        return []

    closed_ids: set[str] = set()
    created: list[OpenLoopEvent] = []
    for line_no, raw in enumerate(raw_lines, start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("strand/open_loops: bad line %d: %s", line_no, exc)
            continue
        if not isinstance(payload, dict):
            continue
        event_type = payload.get("event_type")
        if event_type in ("open_loop_closed", "promise_paid_off"):
            closed_by = payload.get("closed_by_event")
            if isinstance(closed_by, str) and closed_by:
                closed_ids.add(closed_by)
            continue
        if event_type != "open_loop_created":
            continue
        try:
            created.append(_event_from_dict(payload))
        except (TypeError, ValueError, KeyError) as exc:
            logger.warning("strand/open_loops: bad event line %d: %s", line_no, exc)

    active = [e for e in created if e.event_id not in closed_ids]
    active.sort(key=lambda e: (e.chapter_planted, e.event_id))
    return active


def reader_pull_data(novel_path: Path, current_chapter: int) -> ReaderPullData:
    """Compute the dispatcher loop payload for ``current_chapter``."""
    active = get_active_loops(novel_path)
    by_age = sorted(active, key=lambda e: (e.chapter_planted, e.event_id))
    urgent_sorted = sorted(
        by_age, key=lambda e: _URGENCY_RANK.get(e.urgency, 0), reverse=True
    )
    urgent_loops = urgent_sorted[:LOOP_URGENT_TOP_N]

    horizon = current_chapter + LOOP_DEADLINE_IMMINENT_WINDOW
    deadline_imminent = [
        e
        for e in active
        if e.loop_deadline is not None
        and current_chapter <= e.loop_deadline <= horizon
    ]
    debt_overdue = [
        e
        for e in active
        if e.loop_deadline is not None and e.loop_deadline < current_chapter
    ]
    return ReaderPullData(
        urgent_loops=urgent_loops,
        deadline_imminent=deadline_imminent,
        debt_count=len(active),
        debt_overdue=debt_overdue,
    )


def extract_loops_from_outline(outline_text: str, chapter: int) -> list[OpenLoopEvent]:
    """Heuristically detect new loop intents from an outline draft."""
    if not outline_text:
        return []
    text_lower = outline_text.lower()
    matches: list[tuple[int, str, str]] = []
    for phrase, loop_type in _OUTLINE_LOOP_MARKERS:
        try:
            pattern = re.compile(
                r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                flags=re.IGNORECASE | re.UNICODE,
            )
        except re.error:
            continue
        for hit in pattern.finditer(text_lower):
            matches.append((hit.start(), phrase, loop_type))
    if not matches:
        return []
    matches.sort(key=lambda item: item[0])
    events: list[OpenLoopEvent] = []
    for idx, (pos, phrase, loop_type) in enumerate(matches, start=1):
        events.append(
            OpenLoopEvent(
                event_id=f"loop-ch{chapter:04d}-{idx:03d}",
                event_type="open_loop_created",
                subject=_slugify(phrase),
                chapter_planted=chapter,
                content=_excerpt_around(outline_text, pos, length=100),
                loop_type=loop_type,
                urgency=Urgency.MEDIUM.value,
            )
        )
    return events


def _matches_payoff(loop: OpenLoopEvent, text_lower: str) -> bool:
    """Tiered matching: subject match alone is sufficient; content keywords
    require >= 2 hits to avoid single-word false positives."""
    subject = (loop.subject or "").strip().lower()
    if subject:
        if _word_boundary_match(subject, text_lower):
            return True
        spaced = subject.replace("_", " ").strip()
        if spaced and spaced != subject and _word_boundary_match(spaced, text_lower):
            return True

    content_lower = (loop.content or "").lower()
    content_keywords: list[str] = []
    for token in re.findall(r"\w+", content_lower, flags=re.UNICODE):
        if len(token) < _PAYOFF_MIN_TOKEN_LEN or token in _PAYOFF_STOP_WORDS:
            continue
        content_keywords.append(token)

    if not content_keywords:
        return False
    hit_count = sum(
        1 for kw in set(content_keywords) if _word_boundary_match(kw, text_lower)
    )
    return hit_count >= 2


def detect_loop_payoff(
    chapter_text: str, active_loops: list[OpenLoopEvent]
) -> list[OpenLoopEvent]:
    """Heuristically detect which active loops the chapter just resolved."""
    if not chapter_text or not active_loops:
        return []
    text_lower = chapter_text.lower()
    closures: list[OpenLoopEvent] = []
    for original in active_loops:
        if _matches_payoff(original, text_lower):
            closures.append(
                OpenLoopEvent(
                    event_id=f"close-{original.event_id}",
                    event_type="open_loop_closed",
                    subject=original.subject,
                    chapter_planted=original.chapter_planted,
                    content=f"Detected payoff for {original.subject}",
                    loop_type=original.loop_type,
                    urgency=original.urgency,
                    chapter_closed=None,
                    resolution="fulfilled",
                    closed_by_event=original.event_id,
                )
            )
    return closures


# --------------------------------------------------------------------------- #
# Plot-thread migration (ported from migrate_plot_threads_to_loops.py)
# --------------------------------------------------------------------------- #

_MIGRATE_LOOP_TYPE_MARKERS: tuple[tuple[str, str], ...] = (
    ("hứa", LoopType.VOW.value),
    ("thề", LoopType.VOW.value),
    ("đính ước", LoopType.VOW.value),
    ("bí ẩn", LoopType.MYSTERY.value),
    ("bí mật", LoopType.MYSTERY.value),
    ("đe dọa", LoopType.THREAT.value),
    ("kẻ thù", LoopType.THREAT.value),
    ("đại nạn", LoopType.THREAT.value),
    ("huyết mạch", LoopType.INHERITANCE.value),
    ("thân thế", LoopType.INHERITANCE.value),
    ("kế thừa", LoopType.INHERITANCE.value),
    ("nợ", LoopType.DEBT.value),
    ("lời nguyền", LoopType.CURSE.value),
    ("ấn ký", LoopType.CURSE.value),
    ("phong ấn", LoopType.CURSE.value),
)
_MIGRATE_HIGH_URGENCY_MARKERS: tuple[str, ...] = (
    "high", "critical", "urgent", "khẩn cấp", "nguy cấp",
)
_MIGRATE_CHAPTER_RE = re.compile(
    r"(?:chương|chapter|ch\.?)\s*(\d{1,4})", flags=re.IGNORECASE | re.UNICODE
)


def _migrate_split_sections(text: str) -> list[tuple[str, str]]:
    if not text:
        return []
    h2_split = re.split(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    if len(h2_split) > 1:
        return _pairs_from_split(h2_split)
    h1_split = re.split(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    if len(h1_split) > 1:
        return _pairs_from_split(h1_split)
    return []


def _pairs_from_split(parts: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if heading:
            pairs.append((heading, body))
    return pairs


def _migrate_guess_loop_type(body: str) -> str:
    if not body:
        return LoopType.MYSTERY.value
    body_lower = body.lower()
    for marker, loop_type in _MIGRATE_LOOP_TYPE_MARKERS:
        if marker in body_lower:
            return loop_type
    return LoopType.MYSTERY.value


def _migrate_guess_urgency(body: str) -> str:
    if not body:
        return Urgency.MEDIUM.value
    body_lower = body.lower()
    for marker in _MIGRATE_HIGH_URGENCY_MARKERS:
        if marker in body_lower:
            return Urgency.HIGH.value
    return Urgency.MEDIUM.value


def _migrate_guess_chapter(body: str) -> int:
    if not body:
        return 1
    match = _MIGRATE_CHAPTER_RE.search(body)
    if not match:
        return 1
    try:
        return max(int(match.group(1)), 1)
    except (TypeError, ValueError):
        return 1


def _migrate_first_paragraph(body: str, max_chars: int = 200) -> str:
    if not body:
        return ""
    for para in re.split(r"\n\s*\n", body):
        cleaned = para.strip()
        if cleaned:
            return cleaned[:max_chars]
    return body.strip()[:max_chars]


def _migrate_existing_event_ids(novel_path: Path) -> set[str]:
    path = _event_log_path(novel_path)
    if not path.exists():
        return set()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("strand/open_loops: failed to read %s: %s", path, exc)
        return set()
    ids: set[str] = set()
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            eid = payload.get("event_id")
            if isinstance(eid, str) and eid:
                ids.add(eid)
    return ids


def migrate_plot_threads(novel_path: Path) -> list[OpenLoopEvent]:
    """One-shot migration of ``database/plot_threads/*.md`` into loop events.

    Idempotent: stable ``migrated-…`` event ids are skipped on re-run. The
    original markdown files are left untouched.
    """
    threads_dir = Path(novel_path) / "database" / "plot_threads"
    if not threads_dir.is_dir():
        return []
    existing_ids = _migrate_existing_event_ids(novel_path)
    recorded: list[OpenLoopEvent] = []

    for path in sorted(threads_dir.glob("*.md")):
        if path.name.startswith(".") or path.name.startswith("_"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("strand/migrate: failed to read %s: %s", path, exc)
            continue
        try:
            sections = _migrate_split_sections(text)
        except re.error as exc:
            logger.warning("strand/migrate: failed to split %s: %s", path, exc)
            continue
        if not sections:
            continue

        file_stem_slug = _slugify(path.stem) or path.stem
        seen_slugs: dict[str, int] = {}
        for heading, body in sections:
            heading_slug = _slugify(heading)
            if not heading_slug:
                continue
            count = seen_slugs.get(heading_slug, 0)
            seen_slugs[heading_slug] = count + 1
            unique_slug = heading_slug if count == 0 else f"{heading_slug}-{count + 1}"
            event_id = f"migrated-{file_stem_slug}-{unique_slug}"
            if event_id in existing_ids:
                continue
            event = OpenLoopEvent(
                event_id=event_id,
                event_type="open_loop_created",
                subject=heading_slug,
                chapter_planted=_migrate_guess_chapter(body),
                content=_migrate_first_paragraph(body),
                loop_type=_migrate_guess_loop_type(body),
                urgency=_migrate_guess_urgency(body),
            )
            try:
                record_loop_event(novel_path, event)
            except OSError as exc:
                logger.warning("strand/migrate: failed to record %s: %s", event_id, exc)
                continue
            existing_ids.add(event_id)
            recorded.append(event)
    return recorded


# --------------------------------------------------------------------------- #
# weave — the headline tool interface (design #6)
# --------------------------------------------------------------------------- #


def weave(novel_path: Path, chapter: int) -> dict[str, Any]:
    """``weave(plot_threads, chapter) -> {open_loops, due_payoffs, orphan_seeds}``.

    Reads the open-loop event log under ``novel_path`` and surfaces:

    * ``open_loops``   — every active loop (created, not yet closed).
    * ``due_payoffs``  — loops whose deadline is imminent or already overdue.
    * ``orphan_seeds`` — active loops with no ``expected_payoff`` planned, i.e.
      seeds that were planted but never scheduled to pay off.
    """
    pull = reader_pull_data(novel_path, chapter)
    active = get_active_loops(novel_path)
    due = pull.deadline_imminent + pull.debt_overdue
    orphan_seeds = [e for e in active if e.expected_payoff is None]
    return {
        "chapter": int(chapter),
        "open_loops": [e.to_dict() for e in active],
        "due_payoffs": [e.to_dict() for e in due],
        "orphan_seeds": [e.to_dict() for e in orphan_seeds],
        "debt_count": pull.debt_count,
        "debt_overload": pull.debt_count > LOOP_DEBT_MAX_DEFAULT,
        "urgent_loops": [e.to_dict() for e in pull.urgent_loops],
    }


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_STRAND_TOOL_SCHEMA = {
    "name": "novelkit_strand",
    "description": (
        "Strand weaver: classify chapter strand (quest/fire/constellation), "
        "compute rolling-window pacing, track seed→thread→payoff open loops, "
        "detect open-loop payoffs, and migrate legacy plot threads to loops."
    ),
    "input": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "weave",
                    "detect_strand",
                    "pacing_report",
                    "reader_pull",
                    "extract_loops",
                    "migrate_plot_threads",
                ],
            },
            "novel_path": {"type": "string"},
            "chapter_text": {"type": "string"},
            "outline_text": {"type": "string"},
            "chapter": {"type": "integer"},
            "lookback": {"type": "integer"},
        },
        "required": ["action"],
    },
    "output": {"type": "object"},
}


def strand_tool(
    action: str,
    *,
    novel_path: Optional[str] = None,
    chapter_text: Optional[str] = None,
    outline_text: Optional[str] = None,
    chapter: Optional[int] = None,
    lookback: int = STRAND_PACING_LOOKBACK,
) -> dict[str, Any]:
    """Stateless tool entrypoint dispatching on ``action``."""
    if action == "weave":
        if novel_path is None or chapter is None:
            raise ValueError("weave requires novel_path and chapter")
        return weave(Path(novel_path), chapter)
    if action == "detect_strand":
        if chapter_text is None or chapter is None:
            raise ValueError("detect_strand requires chapter_text and chapter")
        frontmatter, body = parse_frontmatter(chapter_text)
        return detect_strand(body, chapter, frontmatter).to_dict()
    if action == "pacing_report":
        if novel_path is None or chapter is None:
            raise ValueError("pacing_report requires novel_path and chapter")
        return pacing_report(Path(novel_path), chapter, lookback).to_dict()
    if action == "reader_pull":
        if novel_path is None or chapter is None:
            raise ValueError("reader_pull requires novel_path and chapter")
        return reader_pull_data(Path(novel_path), chapter).to_dict()
    if action == "extract_loops":
        if outline_text is None or chapter is None:
            raise ValueError("extract_loops requires outline_text and chapter")
        return {
            "events": [e.to_dict() for e in extract_loops_from_outline(outline_text, chapter)]
        }
    if action == "migrate_plot_threads":
        if novel_path is None:
            raise ValueError("migrate_plot_threads requires novel_path")
        return {
            "migrated": [e.to_dict() for e in migrate_plot_threads(Path(novel_path))]
        }
    raise ValueError(f"unknown action {action!r}")


registry.register(
    "novelkit_strand",
    strand_tool,
    schema=_STRAND_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "Strand",
    "ChapterStrand",
    "PacingReport",
    "LoopType",
    "Urgency",
    "OpenLoopEvent",
    "ReaderPullData",
    "load_strand_keywords",
    "detect_strand",
    "parse_frontmatter",
    "load_strand_metadata",
    "write_strand_metadata",
    "record_chapter_strand",
    "read_chapter_strand",
    "pacing_report",
    "record_loop_event",
    "get_active_loops",
    "reader_pull_data",
    "extract_loops_from_outline",
    "detect_loop_payoff",
    "migrate_plot_threads",
    "weave",
    "strand_tool",
]
