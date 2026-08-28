"""NovelKit anti-AI-detection tool — AI-flavor detection for Vietnamese prose.

Phase 3 of the migration (Task 8). This self-registering Hermes Custom Tool
**extracts the algorithm** from the legacy ``scripts/ai_flavor_detector.py`` and
re-packages it behind the design's ``detect(text) -> {risk_score, violations[],
fix_hints[]}`` contract (design.md §"Components and Interfaces" #4).

What is ported / added
----------------------
- **Pattern scanning** (Task 8.1): the 5-dimension, externalised pattern engine
  from ``ai_flavor_detector.py`` driven by ``config/ai_flavor_patterns.json``
  (the 9 headline Vietnamese pattern groups — ``light_adverb_verb``,
  ``eye_expression_template``, ``four_stage_closure``, ``parallel_three_clause``,
  ``dramatic_irony_hint``, ``uniform_pacing_marker``, ``felt_very_label``,
  ``info_dump_dialogue``/``info_dump_long_dialogue``, ``self_explaining_motive``
  — plus the auxiliary ``heart_label`` / ``post_dialogue_explanation`` rules).
  Sliding-window and chapter-wide occurrence thresholds are preserved.
- **Burstiness + repetition heuristics** (Task 8.2): sentence-length variation
  (low variation ⇒ uniform "machine" pacing) and repeated sentence/paragraph
  opening structures (cloned openers ⇒ AI flavor). Implemented as additional
  ``AIFlavorViolation``s so they flow through the same risk model.
- **Voice fingerprint check** (Task 8.2): optional per-character dialogue voice
  comparison; near-identical fingerprints across characters signal "voice
  uniform" collapse (Requirement 16.4).
- **Risk model + contract** (Task 8.2 / Requirement 16.3): a bounded
  ``risk_score`` in ``[0, 100]`` with a ``RISK_THRESHOLD`` calibrated so the
  human-like reference corpus stays below it (Property P9 — no false positives)
  while texts containing known AI-flavor patterns rise above it.

Public API
----------
AIFlavorViolation     : dataclass for a single finding (with fix_hint)
AIFlavorResult        : dataclass — risk_score + violations + fix_hints
load_patterns(path?)                       -> dict
detect(text, *, voices=None, config_path?) -> AIFlavorResult
ai_flavor_tool(text, ...)                  -> dict   (registry entrypoint)

Design references: design.md §"Components and Interfaces" #4,
§"Correctness Properties" P9. Validates Requirements 15, 16.

The module is dependency-free (stdlib only); ``tools.registry`` is the single
local import (the Hermes registry shim).
"""

from __future__ import annotations

import json
import logging
import math
import re
import statistics
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from tools import registry

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Default config path — ``<package>/config/ai_flavor_patterns.json``.
#: ``parents[1]`` is the package root (``tools/`` → ``novelkit-hermes/``).
DEFAULT_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[1] / "config" / "ai_flavor_patterns.json"
)

#: Recognised pattern dimensions, in canonical order (ported).
DIMENSIONS: tuple[str, ...] = (
    "vocabulary",
    "syntax",
    "narrative",
    "emotion",
    "dialogue",
)

#: Synthetic dimensions for heuristic (non-regex) signals.
HEURISTIC_DIMENSION = "heuristic"
VOICE_DIMENSION = "voice"

#: Severity ordering: higher = more serious. Drives the risk weighting.
SEVERITY_RANK: dict[str, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "warning": 2,
    "high": 3,
    "error": 4,
}

#: Risk weight contributed by a single violation of each severity.
_SEVERITY_RISK_WEIGHT: dict[str, float] = {
    "info": 2.0,
    "low": 4.0,
    "medium": 9.0,
    "warning": 9.0,
    "high": 16.0,
    "error": 20.0,
}

#: Extra risk per *additional* occurrence beyond the first, per violation.
_OCCURRENCE_RISK_WEIGHT = 2.0
#: Cap on the per-violation occurrence bonus so one rule cannot dominate.
_MAX_OCCURRENCE_BONUS = 12.0

#: Chapters scoring at/above this are flagged ``requires_fix`` (Requirement 16.3).
#: Calibrated against the reference corpus (Property P9): human-like passages
#: stay below, AI-flavored passages rise above.
RISK_THRESHOLD = 35.0

#: Snippet length retained on each violation for the reviewer UI.
_EXCERPT_CHARS = 120

# ---- burstiness / repetition heuristic tuning (Task 8.2) ----
#: Minimum sentences before the burstiness heuristic is meaningful.
_BURSTINESS_MIN_SENTENCES = 6
#: Coefficient-of-variation of sentence lengths below this ⇒ "uniform pacing".
#: Human prose typically varies a lot (CV > 0.4); machine prose clusters tight.
_BURSTINESS_CV_FLOOR = 0.28
#: Words counted per "opener" when measuring repeated sentence/paragraph starts.
_OPENER_WORDS = 3
#: Fraction of openers that must be identical before flagging cloned structure.
_REPEAT_OPENER_RATIO = 0.34
#: Minimum opener samples before the repetition heuristic engages.
_REPEAT_MIN_SAMPLES = 6

# ---- voice fingerprint tuning (Requirement 16.4) ----
#: Cosine similarity between two character voice fingerprints above this ⇒
#: "voice collapse" (characters sound identical).
_VOICE_COLLAPSE_SIMILARITY = 0.97
#: Minimum dialogue tokens per character before a fingerprint is trusted.
_VOICE_MIN_TOKENS = 12
#: Cosine similarity to baseline below this => "voice drift".
_VOICE_DRIFT_SIMILARITY = 0.80
#: Number of checkpoints needed before baseline solidifies.
_VOICE_DRIFT_MIN_CHECKPOINTS = 2
#: Max checkpoints stored per character (trim oldest on write).
_VOICE_DRIFT_MAX_CHECKPOINTS = 20
_VOICE_PROFILES_REL = "logs/voice_profiles.json"


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


@dataclass
class AIFlavorViolation:
    """A single AI-flavor finding (pattern, heuristic, or voice)."""

    dimension: str
    pattern: str
    severity: str
    location: str  # "char_start-char_end" | "window N-M" | "heuristic" | "voice"
    excerpt: str
    fix_hint: str = ""
    occurrence_count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIFlavorResult:
    """Aggregate anti-AI-detection result for one text (design contract #4)."""

    risk_score: float
    violations: list[AIFlavorViolation] = field(default_factory=list)
    fix_hints: list[str] = field(default_factory=list)
    requires_fix: bool = False
    threshold: float = RISK_THRESHOLD
    score_by_dimension: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "violations": [v.to_dict() for v in self.violations],
            "fix_hints": list(self.fix_hints),
            "requires_fix": self.requires_fix,
            "threshold": self.threshold,
            "score_by_dimension": dict(self.score_by_dimension),
        }


# --------------------------------------------------------------------------- #
# Config loading (ported from ai_flavor_detector.load_patterns)
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=8)
def _load_config_cached(path_str: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Load + validate ``ai_flavor_patterns.json`` (cached by path).

    Patterns whose regex fails to compile are dropped (logged), never raised, so
    a single malformed rule cannot crash the detector.
    """
    path = Path(path_str)
    if not path.exists():
        logger.warning("novelkit_ai_flavor: config not found at %s", path)
        return {dim: {} for dim in DIMENSIONS}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("novelkit_ai_flavor: failed to read %s: %s", path, exc)
        return {dim: {} for dim in DIMENSIONS}

    if not isinstance(raw, dict):
        logger.warning(
            "novelkit_ai_flavor: config root must be an object, got %s",
            type(raw).__name__,
        )
        return {dim: {} for dim in DIMENSIONS}

    cleaned: dict[str, dict[str, dict[str, Any]]] = {}
    for dim in DIMENSIONS:
        section = raw.get(dim) or {}
        if not isinstance(section, dict):
            logger.warning("novelkit_ai_flavor: dimension %r must be an object", dim)
            cleaned[dim] = {}
            continue
        valid: dict[str, dict[str, Any]] = {}
        for name, conf in section.items():
            if not isinstance(conf, dict):
                continue
            pattern_src = conf.get("pattern")
            if not isinstance(pattern_src, str) or not pattern_src:
                continue
            try:
                re.compile(pattern_src, flags=re.IGNORECASE | re.UNICODE)
            except re.error as exc:
                logger.warning(
                    "novelkit_ai_flavor: dropping %s.%s — invalid regex: %s",
                    dim,
                    name,
                    exc,
                )
                continue
            valid[name] = dict(conf)
        cleaned[dim] = valid
    return cleaned


def load_patterns(
    path: Optional[Path] = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Load the AI-flavor pattern config (defaults to the package config)."""
    target = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    return _load_config_cached(str(target))


def _clear_pattern_cache() -> None:
    """Test helper — drop the cached config so callers can swap files."""
    _load_config_cached.cache_clear()


# --------------------------------------------------------------------------- #
# Helpers — regex pattern scanning (ported from ai_flavor_detector)
# --------------------------------------------------------------------------- #


def _compile(pattern_src: str) -> re.Pattern[str]:
    return re.compile(pattern_src, flags=re.IGNORECASE | re.UNICODE)


def _make_excerpt(text: str, start: int, end: int) -> str:
    """Slice a small context excerpt around ``[start, end)`` for reporting."""
    if not text:
        return ""
    cushion = max(0, (_EXCERPT_CHARS - (end - start)) // 2)
    real_start = max(0, start - cushion)
    real_end = min(len(text), end + cushion)
    snippet = text[real_start:real_end].strip()
    return re.sub(r"\s+", " ", snippet)[:_EXCERPT_CHARS]


def _count_in_window(
    matches: list[re.Match[str]],
    window_chars: int,
) -> tuple[int, Optional[tuple[int, int]]]:
    """Find the window of ``window_chars`` containing the most matches."""
    if not matches or window_chars <= 0:
        return 0, None
    starts = [m.start() for m in matches]
    best = 0
    best_start = starts[0]
    left = 0
    for right, start in enumerate(starts):
        while start - starts[left] >= window_chars:
            left += 1
        count = right - left + 1
        if count > best:
            best = count
            best_start = starts[left]
    return best, (best_start, best_start + window_chars)


def _scan_dimension(
    dimension: str,
    text: str,
    patterns_for_dim: Mapping[str, dict[str, Any]],
) -> list[AIFlavorViolation]:
    """Apply every pattern in ``patterns_for_dim`` to ``text``.

    Two threshold modes (ported):

    * ``window_chars`` + ``max_occurrences_per_window``: emit when any sliding
      window contains more than the limit.
    * ``max_occurrences``: emit when the chapter-wide count exceeds the limit
      (default 0 ⇒ any single match reported).
    """
    if not text or not patterns_for_dim:
        return []

    violations: list[AIFlavorViolation] = []
    for name, conf in patterns_for_dim.items():
        pattern_src = conf.get("pattern")
        if not isinstance(pattern_src, str):
            continue
        try:
            regex = _compile(pattern_src)
        except re.error:
            continue

        matches = list(regex.finditer(text))
        if not matches:
            continue

        severity = str(conf.get("severity", "medium")).lower()
        fix_hint = str(conf.get("fix_hint", "")).strip()

        window_chars = conf.get("window_chars")
        max_in_window = conf.get("max_occurrences_per_window")
        if isinstance(window_chars, int) and isinstance(max_in_window, int):
            count_in_win, window = _count_in_window(matches, window_chars)
            if count_in_win > max_in_window and window is not None:
                start, end = window
                violations.append(
                    AIFlavorViolation(
                        dimension=dimension,
                        pattern=name,
                        severity=severity,
                        location=f"window {start}-{end}",
                        excerpt=_make_excerpt(text, start, min(end, len(text))),
                        fix_hint=fix_hint,
                        occurrence_count=count_in_win,
                    )
                )
            continue

        max_total = conf.get("max_occurrences", 0)
        if not isinstance(max_total, int):
            max_total = 0
        if len(matches) <= max_total:
            continue
        first = matches[0]
        violations.append(
            AIFlavorViolation(
                dimension=dimension,
                pattern=name,
                severity=severity,
                location=f"{first.start()}-{first.end()}",
                excerpt=_make_excerpt(text, first.start(), first.end()),
                fix_hint=fix_hint,
                occurrence_count=len(matches),
            )
        )
    return violations


# --------------------------------------------------------------------------- #
# Helpers — text segmentation
# --------------------------------------------------------------------------- #

_SENTENCE_SPLIT = re.compile(r"[.!?…]+[\s\"”’)]*|\n+")
_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def split_sentences(text: str) -> list[str]:
    """Split ``text`` into trimmed, non-empty sentences."""
    parts = _SENTENCE_SPLIT.split(text or "")
    return [s.strip() for s in parts if s and s.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split ``text`` into trimmed, non-empty paragraphs (blank-line delimited)."""
    parts = re.split(r"\n\s*\n", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text or "")


def _opener(segment: str, n: int = _OPENER_WORDS) -> str:
    return " ".join(_words(segment)[:n]).lower()


# --------------------------------------------------------------------------- #
# Heuristic 1 — burstiness (sentence-length variation)
# --------------------------------------------------------------------------- #


def sentence_length_cv(text: str) -> Optional[float]:
    """Coefficient of variation (std/mean) of sentence word-counts.

    Returns ``None`` when there are too few sentences to be meaningful. Lower
    values mean uniform pacing (an AI-flavor signal); human prose varies more.
    """
    sentences = split_sentences(text)
    lengths = [len(_words(s)) for s in sentences]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < _BURSTINESS_MIN_SENTENCES:
        return None
    mean = statistics.fmean(lengths)
    if mean <= 0:
        return None
    stdev = statistics.pstdev(lengths)
    return stdev / mean


def detect_burstiness_issue(text: str) -> Optional[AIFlavorViolation]:
    """Flag uniformly-paced prose (low sentence-length variation)."""
    cv = sentence_length_cv(text)
    if cv is None or cv >= _BURSTINESS_CV_FLOOR:
        return None
    return AIFlavorViolation(
        dimension=HEURISTIC_DIMENSION,
        pattern="low_burstiness",
        severity="medium",
        location="heuristic",
        excerpt=f"sentence-length CV={cv:.3f} < {_BURSTINESS_CV_FLOOR}",
        fix_hint=(
            "Nhịp câu quá đều (độ dài câu gần như nhau) — đặc trưng văn máy. "
            "Xen câu rất ngắn và câu dài để tạo burstiness tự nhiên."
        ),
        occurrence_count=1,
    )


# --------------------------------------------------------------------------- #
# Heuristic 2 — repeated sentence/paragraph openers
# --------------------------------------------------------------------------- #


def _most_common_opener_ratio(segments: Iterable[str]) -> tuple[float, str, int]:
    """Return (max repeated-opener ratio, that opener, total samples)."""
    openers = [o for o in (_opener(s) for s in segments) if o]
    total = len(openers)
    if total == 0:
        return 0.0, "", 0
    counts: dict[str, int] = {}
    for o in openers:
        counts[o] = counts.get(o, 0) + 1
    top_opener, top_count = max(counts.items(), key=lambda kv: kv[1])
    return top_count / total, top_opener, total


def detect_repetition_issue(text: str) -> Optional[AIFlavorViolation]:
    """Flag cloned sentence/paragraph opening structures."""
    best_ratio = 0.0
    best_opener = ""
    best_scope = ""
    for scope, segments in (
        ("sentence", split_sentences(text)),
        ("paragraph", split_paragraphs(text)),
    ):
        ratio, opener, total = _most_common_opener_ratio(segments)
        if total < _REPEAT_MIN_SAMPLES:
            continue
        if ratio > best_ratio:
            best_ratio, best_opener, best_scope = ratio, opener, scope

    if best_ratio < _REPEAT_OPENER_RATIO or not best_opener:
        return None
    return AIFlavorViolation(
        dimension=HEURISTIC_DIMENSION,
        pattern="repeated_opener",
        severity="medium",
        location=f"{best_scope} openers",
        excerpt=f"{best_ratio:.0%} of {best_scope}s open with “{best_opener}…”",
        fix_hint=(
            "Nhiều câu/đoạn mở đầu cùng một cấu trúc — dấu hiệu lặp máy móc. "
            "Đa dạng hóa cách mở câu (hành động, đối thoại, hình ảnh)."
        ),
        occurrence_count=1,
    )


# --------------------------------------------------------------------------- #
# Heuristic 3 — voice fingerprint check (Requirement 16.4)
# --------------------------------------------------------------------------- #


def voice_fingerprint(dialogue: str) -> dict[str, float]:
    """Compute a lightweight stylometric fingerprint for one character voice.

    Features are normalised, length-independent ratios so two characters with
    different line counts can still be compared:

    * mean tokens per line, mean chars per token
    * type-token ratio (lexical diversity)
    * question / exclamation / ellipsis ratios
    """
    lines = [l.strip() for l in re.split(r"[\n]+", dialogue or "") if l.strip()]
    tokens = _words(dialogue)
    n_tokens = len(tokens)
    if n_tokens == 0:
        return {}
    sentences = split_sentences(dialogue) or lines or [dialogue]
    n_sent = max(1, len(sentences))
    types = {t.lower() for t in tokens}
    return {
        "tokens_per_sentence": n_tokens / n_sent,
        "chars_per_token": sum(len(t) for t in tokens) / n_tokens,
        "type_token_ratio": len(types) / n_tokens,
        "question_ratio": dialogue.count("?") / n_sent,
        "exclaim_ratio": dialogue.count("!") / n_sent,
        "ellipsis_ratio": (dialogue.count("…") + dialogue.count("...")) / n_sent,
    }


def _cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(a.get(k, 0.0) ** 2 for k in keys))
    nb = math.sqrt(sum(b.get(k, 0.0) ** 2 for k in keys))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def detect_voice_collapse(
    voices: Mapping[str, str],
) -> list[AIFlavorViolation]:
    """Flag near-identical voice fingerprints across characters.

    ``voices`` maps a character name to a concatenation of their dialogue. Pairs
    of characters whose fingerprints are too similar are flagged (Requirement
    16.4 — preserve per-character voice, avoid "uniform voice").
    """
    usable = {
        name: voice_fingerprint(text)
        for name, text in (voices or {}).items()
        if len(_words(text)) >= _VOICE_MIN_TOKENS
    }
    usable = {name: fp for name, fp in usable.items() if fp}
    names = sorted(usable)
    violations: list[AIFlavorViolation] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            sim = _cosine(usable[a], usable[b])
            if sim >= _VOICE_COLLAPSE_SIMILARITY:
                violations.append(
                    AIFlavorViolation(
                        dimension=VOICE_DIMENSION,
                        pattern="voice_collapse",
                        severity="high",
                        location="voice",
                        excerpt=f"{a} ≈ {b} (similarity {sim:.3f})",
                        fix_hint=(
                            f"Giọng của '{a}' và '{b}' gần như trùng nhau — "
                            "đồng phục giọng. Tạo dấu vân giọng riêng (nhịp, từ "
                            "đệm, độ dài câu, thói quen nói) cho từng nhân vật."
                        ),
                        occurrence_count=1,
                    )
                )
    return violations


# --------------------------------------------------------------------------- #
# Risk model
# --------------------------------------------------------------------------- #


def _violation_risk(v: AIFlavorViolation) -> float:
    base = _SEVERITY_RISK_WEIGHT.get(v.severity, _SEVERITY_RISK_WEIGHT["medium"])
    extra = min(
        _MAX_OCCURRENCE_BONUS,
        max(0, v.occurrence_count - 1) * _OCCURRENCE_RISK_WEIGHT,
    )
    return base + extra


def compute_risk_score(violations: Iterable[AIFlavorViolation]) -> float:
    """Aggregate violations into a bounded risk score in ``[0, 100]``.

    A saturating sum keeps the score monotonic in the set of violations (more
    findings never lowers the risk) while preventing any single rule from
    pinning the score at 100.
    """
    total = sum(_violation_risk(v) for v in violations)
    # Soft saturation: large totals approach but never exceed 100.
    score = 100.0 * (1.0 - math.exp(-total / 60.0))
    return round(score, 2)


# --------------------------------------------------------------------------- #
# Public detect() — the design contract #4
# --------------------------------------------------------------------------- #


def detect(
    text: str,
    *,
    voices: Optional[Mapping[str, str]] = None,
    config_path: Optional[Path] = None,
) -> AIFlavorResult:
    """Run pattern + heuristic + voice detection and aggregate the result.

    Args:
        text: chapter prose to analyse.
        voices: optional mapping ``{character_name: dialogue_text}`` for the
            voice-fingerprint check (Requirement 16.4).
        config_path: optional override for the pattern config.

    Returns:
        :class:`AIFlavorResult` with ``risk_score`` (0-100), ``violations`` and
        deduplicated ``fix_hints``; ``requires_fix`` is set when the score meets
        :data:`RISK_THRESHOLD` (Requirement 16.3).
    """
    violations: list[AIFlavorViolation] = []
    if text and text.strip():
        config = load_patterns(config_path)
        for dim in DIMENSIONS:
            violations.extend(_scan_dimension(dim, text, config.get(dim, {})))

        burst = detect_burstiness_issue(text)
        if burst is not None:
            violations.append(burst)
        repeat = detect_repetition_issue(text)
        if repeat is not None:
            violations.append(repeat)

    if voices:
        violations.extend(detect_voice_collapse(voices))

    risk_score = compute_risk_score(violations)

    fix_hints: list[str] = []
    seen: set[str] = set()
    for v in violations:
        if v.fix_hint and v.fix_hint not in seen:
            seen.add(v.fix_hint)
            fix_hints.append(v.fix_hint)

    score_by_dimension: dict[str, int] = {}
    for v in violations:
        score_by_dimension[v.dimension] = score_by_dimension.get(v.dimension, 0) + 1

    return AIFlavorResult(
        risk_score=risk_score,
        violations=violations,
        fix_hints=fix_hints,
        requires_fix=risk_score >= RISK_THRESHOLD,
        threshold=RISK_THRESHOLD,
        score_by_dimension=score_by_dimension,
    )


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_AI_FLAVOR_TOOL_SCHEMA = {
    "name": "novelkit_ai_flavor",
    "description": (
        "Anti-AI-detection: scan Vietnamese prose for AI-flavor patterns, "
        "burstiness/repetition heuristics and voice-fingerprint collapse; "
        "return a bounded risk_score with violations and fix_hints."
    ),
    "input": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Chapter prose to analyse"},
            "voices": {
                "type": "object",
                "description": "Optional {character_name: dialogue_text} map",
                "additionalProperties": {"type": "string"},
            },
        },
        "required": ["text"],
    },
    "output": {
        "type": "object",
        "properties": {
            "risk_score": {"type": "number"},
            "violations": {"type": "array"},
            "fix_hints": {"type": "array", "items": {"type": "string"}},
            "requires_fix": {"type": "boolean"},
            "threshold": {"type": "number"},
            "score_by_dimension": {"type": "object"},
        },
        "required": ["risk_score", "violations", "fix_hints", "requires_fix"],
    },
}


def ai_flavor_tool(
    text: str,
    voices: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """Registry entrypoint: ``(text, voices?) -> AIFlavorResult.to_dict()``."""
    return detect(text, voices=voices).to_dict()


# Self-register at import time (Requirement 6.2 — self-registering tool).
registry.register(
    "novelkit_ai_flavor",
    ai_flavor_tool,
    schema=_AI_FLAVOR_TOOL_SCHEMA,
    module=__name__,
)


# --------------------------------------------------------------------------- #
# Voice drift detection (per-character over time)
# --------------------------------------------------------------------------- #


def _compute_voice_baseline(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    keys: set[str] = set()
    for cp in checkpoints:
        keys.update(cp["fingerprint"].keys())
    averaged = {}
    for k in keys:
        values = [cp["fingerprint"].get(k, 0.0) for cp in checkpoints]
        averaged[k] = sum(values) / len(values)
    return {
        "fingerprint": averaged,
        "chapter_range": [checkpoints[0]["chapter"], checkpoints[-1]["chapter"]],
        "sample_tokens": sum(cp["sample_tokens"] for cp in checkpoints),
    }


def record_voice_checkpoint(
    novel_path: Path,
    chapter: int,
    voices: Mapping[str, str],
) -> None:
    """Persist voice fingerprints for all characters at a character-update checkpoint."""
    profiles_path = novel_path / _VOICE_PROFILES_REL
    profiles_path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {"schema": 1, "profiles": {}}
    if profiles_path.exists():
        try:
            data = json.loads(profiles_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    profiles = data.setdefault("profiles", {})

    for name, dialogue in voices.items():
        tokens = _words(dialogue)
        if len(tokens) < _VOICE_MIN_TOKENS:
            continue
        fp = voice_fingerprint(dialogue)
        if not fp:
            continue
        char_profile = profiles.setdefault(name, {"baseline": None, "checkpoints": []})

        sim_to_baseline: Optional[float] = None
        if char_profile["baseline"] is not None:
            sim_to_baseline = round(_cosine(fp, char_profile["baseline"]["fingerprint"]), 4)

        checkpoint = {
            "chapter": chapter,
            "fingerprint": fp,
            "sample_tokens": len(tokens),
            "similarity_to_baseline": sim_to_baseline,
        }
        char_profile["checkpoints"].append(checkpoint)

        if len(char_profile["checkpoints"]) > _VOICE_MAX_CHECKPOINTS:
            char_profile["checkpoints"] = char_profile["checkpoints"][-_VOICE_MAX_CHECKPOINTS:]

        if (
            char_profile["baseline"] is None
            and len(char_profile["checkpoints"]) >= _VOICE_DRIFT_MIN_CHECKPOINTS
        ):
            char_profile["baseline"] = _compute_voice_baseline(char_profile["checkpoints"])
            for cp in char_profile["checkpoints"]:
                cp["similarity_to_baseline"] = round(
                    _cosine(cp["fingerprint"], char_profile["baseline"]["fingerprint"]), 4
                )

    profiles_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def detect_voice_drift(novel_path: Path) -> list[AIFlavorViolation]:
    """Flag characters whose current voice has drifted from their established baseline."""
    profiles_path = novel_path / _VOICE_PROFILES_REL
    if not profiles_path.exists():
        return []

    try:
        data = json.loads(profiles_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    violations: list[AIFlavorViolation] = []
    for name, profile in data.get("profiles", {}).items():
        baseline = profile.get("baseline")
        if baseline is None:
            continue
        checkpoints = profile.get("checkpoints", [])
        if not checkpoints:
            continue

        latest = checkpoints[-1]
        sim = latest.get("similarity_to_baseline")
        if sim is None:
            sim = _cosine(latest["fingerprint"], baseline["fingerprint"])

        if sim < _VOICE_DRIFT_SIMILARITY:
            violations.append(
                AIFlavorViolation(
                    dimension=VOICE_DIMENSION,
                    pattern="voice_drift",
                    severity="medium",
                    location="voice",
                    excerpt=(
                        f"{name}: similarity to baseline = {sim:.3f} "
                        f"(threshold {_VOICE_DRIFT_SIMILARITY}), "
                        f"baseline chapters {baseline['chapter_range']}, "
                        f"latest chapter {latest['chapter']}"
                    ),
                    fix_hint=(
                        f"Giọng của '{name}' đã trôi xa khỏi baseline ban đầu "
                        f"(similarity {sim:.3f} < {_VOICE_DRIFT_SIMILARITY}). "
                        "Kiểm tra xem nhân vật có đang nói dài hơn/ngắn hơn, "
                        "mất đi thói quen ngôn ngữ đặc trưng không."
                    ),
                    occurrence_count=1,
                )
            )
    return violations


__all__ = [
    "AIFlavorViolation",
    "AIFlavorResult",
    "DIMENSIONS",
    "DEFAULT_CONFIG_PATH",
    "RISK_THRESHOLD",
    "SEVERITY_RANK",
    "load_patterns",
    "split_sentences",
    "split_paragraphs",
    "sentence_length_cv",
    "detect_burstiness_issue",
    "detect_repetition_issue",
    "voice_fingerprint",
    "detect_voice_collapse",
    "record_voice_checkpoint",
    "detect_voice_drift",
    "compute_risk_score",
    "detect",
    "ai_flavor_tool",
]
