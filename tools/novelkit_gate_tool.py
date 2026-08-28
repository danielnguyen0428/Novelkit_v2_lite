"""NovelKit gate tool — unified quality-gate registry + review scoring.

Phase 3 of the migration (Task 6). This Custom Tool **consolidates** four
legacy modules into a single self-registering Hermes tool (finding: gate
sprawl):

- ``validators.py``      — review parsing (score + explicit verdict).
- ``gate_registry.py``   — the genre/common gate registry pattern.
- ``gates/``             — keyword quality gates (language contamination,
                           chapter length, genre texture, …).
- ``semantic_gates/``    — LLM-backed gates (modelled here as a registrable
                           seam; the layer is skippable and off by default so
                           the package stays verifiable without an LLM).

The headline interface (design.md §"Components and Interfaces" #2) is::

    evaluate(chapter, review_file, context) -> Verdict{outcome, score, findings[], flags[]}

What is ported (semantics-preserving)
-------------------------------------
- **7-criteria review scoring** (``REVIEW_CRITERIA``): the reviewer rubric —
  Tầng A universal (6 line items, 60 pts) + Tầng B project voice (40 pts) — sums
  to 100. ``parse_review`` reads the per-criterion table when present, else
  falls back to the labelled/bare total. (Requirement 9.1.)
- **Thresholds + verdict override** (``score_to_outcome`` / ``parse_review``):
  ≥85 PASS, 70-84 SOFT-FAIL, <70 HARD-FAIL; an explicit verdict
  (PASSED/SOFT-FAIL/HARD-FAIL) always wins over the score band. Ported from
  ``validators.parse_review_outcome``. (Requirement 9.2; Property P2.)
- **Early Chapter Score Lift** (chapters 1-5): the thresholds are **not**
  lowered; instead the gate demands on-page evidence (scene promise, Core
  Wound, World Pressure, micro-payoff) and emits an evidence finding +
  ``EARLY_CHAPTER_SCORE_LIFT`` flag when the bar is not met. (Requirement 9.3.)
- **Harem Progression** (``detect_harem_voice_collapse``): when PROJECT_DNA
  declares harem/đa-tuyến-tình, the gate audits female-line voice fingerprints
  and raises the ``HAREM_VOICE_COLLAPSE`` flag when distinct love-interest
  voices collapse into one. (Requirement 9.4.)

The module is dependency-free (stdlib only) so it is verifiable in isolation;
the only local imports are ``tools.registry`` (the Hermes registry shim) and
the shared review thresholds from ``tools.novelkit_pipeline_tool`` (reused, not
re-declared, so the gate and pipeline never diverge — context constraint).

Design references: design.md §"Components and Interfaces" #2, §"Data Models"
(Verdict), §"Correctness Properties" P2.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable, Optional

from tools import registry

# Reuse the canonical review thresholds — DO NOT re-declare divergent values.
from tools.novelkit_pipeline_tool import (
    REVIEW_PASS_SCORE,
    REVIEW_SOFT_FAIL_SCORE,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Chapters 1..N get the Early Chapter Score Lift contract (Requirement 9.3).
EARLY_CHAPTER_MAX = 5

#: Outcomes used by the Verdict (design.md §"Data Models" → Verdict).
OUTCOME_DONE = "done"
OUTCOME_SOFT_FAIL = "soft_fail"
OUTCOME_HARD_FAIL = "hard_fail"
OUTCOME_BLOCKED = "blocked"

#: Genres that may register genre-specific gates (ported from gate_registry).
SUPPORTED_GENRES = frozenset(
    {"xianxia", "urban", "romance", "time_travel", "scifi", "meta_genre"}
)

#: PROJECT_DNA markers that declare a harem / multi-romance novel
#: (ported from dispatcher_adapter._novel_declares_harem).
_HAREM_DNA_MARKERS = (
    "harem",
    "đa tuyến tình",
    "da tuyen tinh",
    "chính thất",
    "chinh that",
    "đạo lữ",
    "dao lu",
    "hậu cung",
    "hau cung",
)


# --------------------------------------------------------------------------- #
# The 7-criteria review rubric (reviewer SOUL.md — Tầng A + Tầng B = 100)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Criterion:
    """One line item of the review rubric."""

    key: str
    label: str
    max_points: int
    tier: str  # "A" universal · "B" project voice


#: The 7 review criteria. Tầng A universal (60) + Tầng B project voice (40) = 100.
REVIEW_CRITERIA: tuple[Criterion, ...] = (
    Criterion("logic_consistency", "Logic Consistency", 15, "A"),
    Criterion("character_integrity", "Character Integrity", 12, "A"),
    Criterion("plot_advancement", "Plot Advancement", 10, "A"),
    Criterion("timeline_continuity", "Timeline & Continuity", 8, "A"),
    Criterion("prose_fundamentals", "Prose Fundamentals", 10, "A"),
    Criterion("hook_micropayoff", "Hook & Micro-payoff", 5, "A"),
    # Keep the persisted key for backwards compatibility; only the label changes.
    Criterion("author_style", "Project Voice", 40, "B"),
)

REVIEW_MAX_SCORE = sum(c.max_points for c in REVIEW_CRITERIA)  # == 100

TYPED_REVIEW_DIMENSIONS = (
    "plot_progression",
    "character_consistency",
    "continuity",
    "prose_quality",
    "dialogue_voice",
    "world_consistency",
    "reader_momentum",
)
CRITICAL_TYPED_REVIEW_DIMENSIONS = (
    "character_consistency",
    "continuity",
    "world_consistency",
)
GATE_POLICY_ID = "hermes_default_v1"


# --------------------------------------------------------------------------- #
# ValidationIssue + Verdict (design.md §"Data Models")
# --------------------------------------------------------------------------- #


@dataclass
class ValidationIssue:
    """A single quality-gate finding (compatible with the legacy record)."""

    code: str
    severity: str  # "error" (hard-block) · "warning" (watchlist) · "info"
    message: str
    path: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Verdict:
    """Gate verdict (design.md §"Data Models" → Verdict)."""

    outcome: str  # done | soft_fail | hard_fail | blocked
    score: Optional[float]
    findings: list[ValidationIssue] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "score": self.score,
            "findings": [f.to_dict() for f in self.findings],
            "flags": list(self.flags),
        }


# --------------------------------------------------------------------------- #
# Review parsing — score + explicit verdict (ported from validators.py)
# --------------------------------------------------------------------------- #

# Labelled score wins over a stray "85/100" in lore quotes / example targets.
_REVIEW_LABELED_SCORE_RE = re.compile(
    r"(?:Score\s*Override|Điểm|Score|Final\s*Score|Kết\s*Quả|Total\s*Score|"
    r"Override|TỔNG|TONG)\s*[:\-–—]?\s*\**\s*(\d{1,3}(?:\.\d+)?)\s*/\s*100",
    re.IGNORECASE,
)
_REVIEW_BARE_SCORE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*/\s*100")

# Per-criterion table rows: "| Logic Consistency | 13/15 | ... |" or "| .. | 13 |".
def _criterion_row_re(label: str) -> re.Pattern[str]:
    return re.compile(
        r"^\s*\|?\s*\**\s*"
        + re.escape(label)
        + r"\s*\**\s*\|\s*\**\s*(\d{1,3}(?:\.\d+)?)\s*(?:/\s*\d{1,3})?\s*\**\s*\|",
        re.IGNORECASE | re.MULTILINE,
    )


_REVIEW_PASS_TOKENS = (
    "PASS", "PASSED", "OK", "SUCCESS", "SUCCESS_WITH_FLAGS", "PASS_WITH_FLAGS",
)
_REVIEW_HARD_FAIL_TOKENS = (
    "HARD_FAIL", "HARDFAIL", "FAIL", "FAILED", "FAIL_WITH_FLAGS",
    "BLOCKED", "BLOCK", "NEEDS_REWRITE", "REWRITE", "HARD_FAIL_DEPTH",
)
_REVIEW_SOFT_FAIL_TOKENS = (
    "SOFT_FAIL", "SOFTFAIL", "WARN", "WARNING", "WARN_WITH_FLAGS",
    "SOFT_FAIL_STYLE",
)

_REVIEW_STRONG_VERDICT_LABELS = (
    r"(?:(?:Operational|Final|Review)\s+Verdict|Review\s+Outcome|Final\s+Ruling|"
    r"Trạng\s*thái|Overall|Verdict|Status|Outcome|Decision|Final)"
)
_REVIEW_WEAK_VERDICT_LABELS = r"(?:Kết\s*(?:luận|quả)|Conclusion)"
_REVIEW_VERDICT_HEADING_PREFIX = (
    r"^\s*#{1,6}\s*(?:(?:[IVXLCDM]+|\d+)(?:\.\d+)*[\.)]?\s*)?(?:[-–—]\s*)?\**\s*"
)

_REVIEW_STRONG_VERDICT_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?\**\s*"
    + _REVIEW_STRONG_VERDICT_LABELS
    + r"\**\s*[:\-–—]\s*\**\s*[`'\"“‘]?\s*"
    r"(?:[^\x00-\x7F]\s*)*"
    r"([A-Za-z][A-Za-z0-9_\- ]{1,30})",
    re.IGNORECASE | re.MULTILINE,
)
_REVIEW_STRONG_VERDICT_HEADING_RE = re.compile(
    _REVIEW_VERDICT_HEADING_PREFIX + _REVIEW_STRONG_VERDICT_LABELS + r"\s*\**\s*$",
    re.IGNORECASE,
)
_REVIEW_WEAK_VERDICT_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?\**\s*"
    + _REVIEW_WEAK_VERDICT_LABELS
    + r"\**\s*[:\-–—]\s*\**\s*[`'\"“‘]?\s*"
    r"(?:[^\x00-\x7F]\s*)*"
    r"([A-Za-z][A-Za-z0-9_\- ]{1,30})",
    re.IGNORECASE | re.MULTILINE,
)
_REVIEW_WEAK_VERDICT_HEADING_RE = re.compile(
    _REVIEW_VERDICT_HEADING_PREFIX + _REVIEW_WEAK_VERDICT_LABELS + r"\s*\**\s*$",
    re.IGNORECASE,
)
_REVIEW_VERDICT_VALUE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?\**\s*[`'\"“‘]?\s*"
    r"(?:Chapter\s+\d+\s*[:\-–—]\s*)?"
    r"(?:[^\x00-\x7F]\s*)*"
    r"([A-Za-z][A-Za-z0-9_\- ]{1,30})",
    re.IGNORECASE,
)

# Words marking a line as a *threshold rule label* / negated phrase rather than
# a real verdict (e.g. "Hard-fail range: …", "không hard-fail").
_LEGACY_DESCRIPTOR_WORDS = (
    "range", "limit", "threshold", "zone", "minimum", "min ",
    "phạm vi", "khoảng", "giới hạn", "ngưỡng", "vùng", "tối thiểu",
    "không ", "no ", "not ", "chưa ", "ngoài ",
)


def _legacy_outcome_signal(text: str, pattern: re.Pattern[str]) -> bool:
    for line in text.splitlines():
        if not pattern.search(line):
            continue
        lower = line.lower()
        if any(word in lower for word in _LEGACY_DESCRIPTOR_WORDS):
            continue
        return True
    return False


def _classify_verdict_token(raw: str, *, allow_fuzzy: bool = True) -> Optional[str]:
    """Map a verdict token (e.g. 'SUCCESS_WITH_FLAGS') → 'pass'/'soft_fail'/'hard_fail'."""
    normalised = re.sub(r"[\s\-]+", "_", raw.strip().upper()).strip("_")
    if normalised in _REVIEW_PASS_TOKENS:
        return "pass"
    if normalised in _REVIEW_HARD_FAIL_TOKENS:
        return "hard_fail"
    if normalised in _REVIEW_SOFT_FAIL_TOKENS:
        return "soft_fail"
    if not allow_fuzzy:
        return None
    # Hard-fail beats pass — a token mentioning both is treated as fail.
    has_fail = "FAIL" in normalised or "BLOCK" in normalised
    has_warn = "WARN" in normalised or "SOFT" in normalised
    has_pass = "PASS" in normalised or "SUCCESS" in normalised or normalised == "OK"
    if has_fail and has_warn:
        return "soft_fail"
    if has_fail and not has_warn:
        return "hard_fail"
    if has_warn and not has_fail:
        return "soft_fail"
    if has_pass and not has_fail and not has_warn:
        return "pass"
    return None


def _iter_review_verdict_tokens(
    text: str, *, line_re: re.Pattern[str], heading_re: re.Pattern[str]
):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        inline = line_re.match(line)
        if inline:
            yield inline.group(1)
            continue
        if not heading_re.match(line):
            continue
        for candidate in lines[index + 1:]:
            stripped = candidate.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                sub_text = stripped.lstrip("#").strip()
                if sub_text:
                    value = _REVIEW_VERDICT_VALUE_RE.match(sub_text)
                    if value:
                        yield value.group(1)
                break
            value = _REVIEW_VERDICT_VALUE_RE.match(stripped)
            if value:
                yield value.group(1)
            break


@dataclass(frozen=True)
class ReviewParse:
    """Parsed review signal: score, explicit verdict, per-criterion scores."""

    score: Optional[float]
    verdict: Optional[str]  # pass | soft_fail | hard_fail | None
    criteria_scores: dict[str, float] = field(default_factory=dict)
    criteria_total: Optional[float] = None


def _parse_criteria_scores(text: str) -> dict[str, float]:
    """Extract per-criterion scores from the review rubric table."""
    scores: dict[str, float] = {}
    for crit in REVIEW_CRITERIA:
        match = _criterion_row_re(crit.label).search(text)
        if match:
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            # Clamp to the criterion ceiling (defensive against typos).
            scores[crit.key] = min(value, float(crit.max_points))
    return scores


def parse_review_text(text: str) -> ReviewParse:
    """Parse a review document into (score, verdict, per-criterion scores).

    Score resolution order (ported from validators.parse_review_outcome):
      1. Sum of the per-criterion rubric table when *all 7* criteria are found.
      2. A labelled total ("TỔNG: 88/100", "Điểm: 88/100", "Score: 88/100").
      3. The last bare "NN/100".
    Verdict resolution: human override > strong verdict line/heading >
    weak conclusion line > legacy keyword fallback. Explicit verdict always
    wins over score downstream (Property P2).
    """
    criteria_scores = _parse_criteria_scores(text)
    criteria_total: Optional[float] = None
    if len(criteria_scores) == len(REVIEW_CRITERIA):
        criteria_total = float(sum(criteria_scores.values()))

    if criteria_total is not None:
        score: Optional[float] = criteria_total
    else:
        labeled = list(_REVIEW_LABELED_SCORE_RE.finditer(text))
        if labeled:
            score = round(float(labeled[-1].group(1)))
        else:
            bare = list(_REVIEW_BARE_SCORE_RE.finditer(text))
            score = round(float(bare[-1].group(1))) if bare else None

    # 1) Human override always wins.
    if re.search(r"(?:##\s+Human Approval|APPROVED BY HUMAN)", text, re.IGNORECASE):
        return ReviewParse(score, "pass", criteria_scores, criteria_total)

    # 2) Strong verdict line(s) — last verdict wins.
    last_verdict: Optional[str] = None
    for token in _iter_review_verdict_tokens(
        text,
        line_re=_REVIEW_STRONG_VERDICT_LINE_RE,
        heading_re=_REVIEW_STRONG_VERDICT_HEADING_RE,
    ):
        classified = _classify_verdict_token(token)
        if classified is not None:
            last_verdict = classified
    if last_verdict is not None:
        return ReviewParse(score, last_verdict, criteria_scores, criteria_total)

    # 3) Weak conclusion labels (no fuzzy matching).
    last_weak: Optional[str] = None
    for token in _iter_review_verdict_tokens(
        text,
        line_re=_REVIEW_WEAK_VERDICT_LINE_RE,
        heading_re=_REVIEW_WEAK_VERDICT_HEADING_RE,
    ):
        classified = _classify_verdict_token(token, allow_fuzzy=False)
        if classified is not None:
            last_weak = classified
    if last_weak is not None:
        return ReviewParse(score, last_weak, criteria_scores, criteria_total)

    # 4) Legacy keyword fallback (skips threshold-rule labels).
    if _legacy_outcome_signal(text, re.compile(r"\bHARD[\s_-]?FAIL\b", re.IGNORECASE)):
        return ReviewParse(score, "hard_fail", criteria_scores, criteria_total)
    if _legacy_outcome_signal(text, re.compile(r"\bSOFT[\s_-]?FAIL\b", re.IGNORECASE)):
        return ReviewParse(score, "soft_fail", criteria_scores, criteria_total)
    if _legacy_outcome_signal(text, re.compile(r"\bPASS(?:ED)?\b", re.IGNORECASE)):
        return ReviewParse(score, "pass", criteria_scores, criteria_total)
    return ReviewParse(score, None, criteria_scores, criteria_total)


def parse_review_file(review_file: "str | Path") -> ReviewParse:
    """Parse a review file from disk (UTF-8). Missing/unreadable → empty parse."""
    path = Path(review_file)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ReviewParse(None, None)
    return parse_review_text(text)


# --------------------------------------------------------------------------- #
# Threshold + verdict override (Property P2)
# --------------------------------------------------------------------------- #


def score_to_outcome(score: Optional[float], verdict: Optional[str] = None) -> str:
    """Map (score, explicit verdict) → outcome (Requirement 9.1/9.2 · P2).

    Explicit verdict (pass/soft_fail/hard_fail) ALWAYS wins over the score
    band. Without a verdict the bands apply: ≥85 done, 70-84 soft_fail, else
    hard_fail. A missing score with no verdict is hard_fail (cannot pass blind).
    """
    if verdict in ("pass", "soft_fail", "hard_fail"):
        return OUTCOME_DONE if verdict == "pass" else verdict
    if score is None:
        return OUTCOME_HARD_FAIL
    if score >= REVIEW_PASS_SCORE:
        return OUTCOME_DONE
    if score >= REVIEW_SOFT_FAIL_SCORE:
        return OUTCOME_SOFT_FAIL
    return OUTCOME_HARD_FAIL


def _round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _policy_digest() -> str:
    payload = {
        "policy_id": GATE_POLICY_ID,
        "dimensions": list(TYPED_REVIEW_DIMENSIONS),
        "critical_dimensions": list(CRITICAL_TYPED_REVIEW_DIMENSIONS),
        "pass_score": REVIEW_PASS_SCORE,
        "soft_fail_score": REVIEW_SOFT_FAIL_SCORE,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def derive_typed_review(
    *,
    review_id: str,
    chapter: int,
    attempt: int,
    draft_sha256: str,
    dimensions: dict[str, float],
    issues: Optional[list[dict[str, Any]]] = None,
    contract_status: Optional[dict[str, Any]] = None,
    rules_digest: Optional[str] = None,
    reviewer_model_fingerprint: Optional[str] = None,
    supersedes: Optional[str] = None,
) -> dict[str, Any]:
    missing = [key for key in TYPED_REVIEW_DIMENSIONS if key not in dimensions]
    if missing:
        raise ValueError(f"missing typed review dimensions: {', '.join(missing)}")
    normalized_dimensions = {
        key: max(0, min(100, int(dimensions[key])))
        for key in TYPED_REVIEW_DIMENSIONS
    }
    overall = _round_half_up(
        sum(normalized_dimensions.values()) / len(TYPED_REVIEW_DIMENSIONS)
    )
    normalized_issues = list(issues or [])
    normalized_contract = contract_status or {"status": "met", "misses": []}
    has_contract_miss = bool(normalized_contract.get("misses")) or (
        normalized_contract.get("status") not in (None, "met")
    )
    has_critical_issue = any(
        issue.get("severity") == "critical" for issue in normalized_issues
    )
    has_critical_dimension_fail = any(
        normalized_dimensions[key] < 60 for key in CRITICAL_TYPED_REVIEW_DIMENSIONS
    )

    if has_contract_miss or has_critical_issue or has_critical_dimension_fail:
        gate_outcome = "rewrite"
    elif overall < REVIEW_SOFT_FAIL_SCORE:
        gate_outcome = "rewrite"
    elif overall < REVIEW_PASS_SCORE:
        gate_outcome = "polish"
    else:
        gate_outcome = "pass"

    final_action = {
        "pass": "sync",
        "polish": "queue_polish",
        "rewrite": "queue_rewrite",
    }[gate_outcome]
    return {
        "schema_version": 2,
        "review_id": review_id,
        "chapter": chapter,
        "attempt": attempt,
        "draft_sha256": draft_sha256,
        "overall_score": overall,
        "gate_outcome": gate_outcome,
        "final_action": final_action,
        "dimensions": normalized_dimensions,
        "issues": normalized_issues,
        "contract_status": normalized_contract,
        "rules_digest": rules_digest,
        "gate_policy_id": GATE_POLICY_ID,
        "gate_policy_digest": _policy_digest(),
        "reviewer_model_fingerprint": reviewer_model_fingerprint,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "supersedes": supersedes,
    }


# --------------------------------------------------------------------------- #
# Early Chapter Score Lift (Requirement 9.3)
# --------------------------------------------------------------------------- #

#: On-page evidence markers an early chapter must show (does NOT lower the bar).
_EARLY_EVIDENCE_MARKERS = (
    ("scene_promise", ("scene promise", "lời hứa cảnh", "scene vitality")),
    ("core_wound", ("core wound", "vết thương lõi", "vết thương cốt lõi")),
    ("world_pressure", ("world pressure", "áp lực thế giới")),
    ("micro_payoff", ("micro-payoff", "micro payoff", "trả nhỏ", "payoff")),
)


def early_chapter_evidence_gaps(text: str) -> list[str]:
    """Return the evidence markers missing from an early-chapter review/chapter."""
    lower = (text or "").lower()
    missing: list[str] = []
    for marker, needles in _EARLY_EVIDENCE_MARKERS:
        if not any(needle in lower for needle in needles):
            missing.append(marker)
    return missing


# --------------------------------------------------------------------------- #
# Harem Progression — voice-collapse detection (Requirement 9.4)
# --------------------------------------------------------------------------- #


def novel_declares_harem(project_dna_metadata: dict[str, Any]) -> bool:
    """True when PROJECT_DNA metadata declares harem / multi-romance.

    Ported from dispatcher_adapter._novel_declares_harem: an explicit truthy
    ``harem`` field, or any harem marker present in the DNA text fields.
    """
    if not isinstance(project_dna_metadata, dict):
        return False
    raw = project_dna_metadata.get("harem")
    if isinstance(raw, bool) and raw:
        return True
    if isinstance(raw, str) and raw.strip().lower() in {"1", "true", "yes", "on", "có"}:
        return True
    blob = " ".join(
        str(v) for v in project_dna_metadata.values() if isinstance(v, (str, int, float))
    ).casefold()
    return any(marker in blob for marker in _HAREM_DNA_MARKERS)


# Dialogue line: a quoted span ("…", “…”, or — em-dash speech) preceded on the
# same/earlier line by a capitalised speaker name + a speech verb or colon.
_DIALOGUE_RE = re.compile(
    r"([\"“][^\"”]{2,}[\"”])",
)
_SPEAKER_RE = re.compile(
    r"([A-ZĐÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ]"
    r"[\wÀ-ỹ]+(?:\s+[A-ZĐÀ-Ỹ][\wÀ-ỹ]+){0,2})"
)

_VOICE_STOPWORDS = frozenset(
    {
        "và", "là", "của", "có", "không", "một", "những", "the", "a", "an",
        "ta", "ngươi", "ngài", "ạ", "à", "ơi", "thì", "mà", "rồi", "đi",
    }
)


def _attribute_dialogue(text: str, speakers: list[str]) -> dict[str, list[str]]:
    """Attribute quoted dialogue lines to the nearest preceding known speaker.

    Returns a mapping ``speaker -> [dialogue strings]``. A line is attributed to
    a speaker when that speaker's name appears within the 120 characters before
    the quote (a sentence-scale window). Speakers are matched case-sensitively
    against the provided ``speakers`` list.
    """
    attributed: dict[str, list[str]] = {s: [] for s in speakers}
    for match in _DIALOGUE_RE.finditer(text):
        quote = match.group(1).strip("\"“”").strip()
        if len(quote) < 3:
            continue
        window = text[max(0, match.start() - 120): match.start()]
        nearest_speaker = None
        nearest_pos = -1
        for speaker in speakers:
            pos = window.rfind(speaker)
            if pos > nearest_pos:
                nearest_pos = pos
                nearest_speaker = speaker
        if nearest_speaker is not None:
            attributed[nearest_speaker].append(quote)
    return attributed


def _voice_fingerprint(lines: list[str]) -> frozenset[str]:
    """Compute a lexical voice fingerprint: the set of significant tokens used."""
    tokens: set[str] = set()
    for line in lines:
        for word in re.findall(r"[\wÀ-ỹ]+", line.lower()):
            if len(word) >= 2 and word not in _VOICE_STOPWORDS:
                tokens.add(word)
    return frozenset(tokens)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass(frozen=True)
class HaremVoiceReport:
    collapsed: bool
    pairs: list[tuple[str, str, float]] = field(default_factory=list)
    speakers_analyzed: list[str] = field(default_factory=list)


#: Two love-interest voices are "collapsed" when their fingerprints overlap
#: at/above this Jaccard similarity (and both have enough dialogue to judge).
HAREM_VOICE_COLLAPSE_THRESHOLD = 0.8
HAREM_MIN_DIALOGUE_LINES = 2


def detect_harem_voice_collapse(
    chapter_text: str, love_interests: list[str]
) -> HaremVoiceReport:
    """Detect collapsed female-line voices across declared love interests.

    For each pair of love interests that each speak ≥ ``HAREM_MIN_DIALOGUE_LINES``
    attributed lines, compute the Jaccard similarity of their voice
    fingerprints; a pair at/above :data:`HAREM_VOICE_COLLAPSE_THRESHOLD` is a
    collapse (Requirement 9.4 — "nhiều tuyến nữ trùng giọng"). With fewer than
    two analysable speakers there is nothing to collapse.
    """
    speakers = [s for s in dict.fromkeys(love_interests) if s and s.strip()]
    if len(speakers) < 2 or not chapter_text:
        return HaremVoiceReport(False, [], speakers)

    attributed = _attribute_dialogue(chapter_text, speakers)
    fingerprints: dict[str, frozenset[str]] = {}
    for speaker in speakers:
        lines = attributed.get(speaker, [])
        if len(lines) >= HAREM_MIN_DIALOGUE_LINES:
            fingerprints[speaker] = _voice_fingerprint(lines)

    analysable = sorted(fingerprints)
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(analysable)):
        for j in range(i + 1, len(analysable)):
            a, b = analysable[i], analysable[j]
            sim = _jaccard(fingerprints[a], fingerprints[b])
            if sim >= HAREM_VOICE_COLLAPSE_THRESHOLD:
                pairs.append((a, b, round(sim, 3)))
    return HaremVoiceReport(bool(pairs), pairs, analysable)


# --------------------------------------------------------------------------- #
# Gate registry (consolidates gate_registry.py + gates/ + semantic seam)
# --------------------------------------------------------------------------- #

# (novel_path, chapter_number, chapter_text, review_text, dna) -> [ValidationIssue]
GateFunction = Callable[
    [Path, int, str, str, dict[str, Any]], list[ValidationIssue]
]


@dataclass
class GateEntry:
    name: str
    function: GateFunction
    is_common: bool = False


class GateRegistry:
    """Unified registry: common gates (all genres) + genre-specific gates.

    Consolidates the legacy ``gate_registry.GateRegistry`` and the gate
    functions previously scattered across ``gates/`` and ``semantic_gates/``
    into one place (Task 6.1 — gate sprawl). ``execute_gates`` catches per-gate
    exceptions so one broken gate can never sink the whole review.
    """

    def __init__(self) -> None:
        self._common_gates: list[GateEntry] = []
        self._genre_gates: dict[str, list[GateEntry]] = {
            g: [] for g in SUPPORTED_GENRES
        }

    def register(self, genre: str, gate_name: str, fn: GateFunction) -> None:
        if genre not in SUPPORTED_GENRES:
            raise ValueError(
                f"Unsupported genre '{genre}'. Supported: {sorted(SUPPORTED_GENRES)}"
            )
        self._genre_gates[genre].append(GateEntry(gate_name, fn))

    def register_common(self, gate_name: str, fn: GateFunction) -> None:
        self._common_gates.append(GateEntry(gate_name, fn, is_common=True))

    def get_gates(self, genre: str) -> list[GateEntry]:
        common = list(self._common_gates)
        if genre in SUPPORTED_GENRES:
            return common + list(self._genre_gates.get(genre, []))
        return common  # unknown genre still runs the common gates

    def execute_gates(
        self,
        genre: str,
        novel_path: Path,
        chapter_number: int,
        chapter_text: str,
        review_text: str,
        project_dna_metadata: dict[str, Any],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for gate in self.get_gates(genre):
            try:
                result = gate.function(
                    novel_path,
                    chapter_number,
                    chapter_text,
                    review_text,
                    project_dna_metadata,
                )
                if isinstance(result, list):
                    issues.extend(result)
            except Exception as exc:  # one bad gate must not sink the review
                issues.append(
                    ValidationIssue(
                        code=f"GATE_EXCEPTION_{gate.name.upper()}",
                        severity="warning",
                        message=f"Gate '{gate.name}' failed to execute: {exc}",
                    )
                )
        return issues

    @property
    def common_gate_names(self) -> list[str]:
        return [g.name for g in self._common_gates]

    @property
    def genre_gate_names(self) -> dict[str, list[str]]:
        return {g: [e.name for e in gs] for g, gs in self._genre_gates.items()}


# ---- Common keyword gates (ported from gates/common.py) ------------------- #

_OPERATIONAL_BANNED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:task_runner|control_plane|dispatcher|pipeline|runtime)\b", re.IGNORECASE),
    re.compile(r"\b(?:verify.output|record_task|sync_repair|auto.advance)\b", re.IGNORECASE),
    re.compile(r"\b(?:COMPLETED_WITH_FLAGS|SOFT_FAIL|HARD_FAIL|PASS_WITH_FLAGS)\b"),
    re.compile(r"\b(?:checkpoint|watchlist|circuit.breaker|breaker_state)\b", re.IGNORECASE),
    re.compile(r"\b(?:token_budget|max_turns|failover|provider_rate_limit)\b", re.IGNORECASE),
    re.compile(r"\b(?:metadata|workflow|debug)\b", re.IGNORECASE),
)


def language_guard_gate(
    novel_path: Path,
    chapter_number: int,
    chapter_text: str,
    review_text: str,
    project_dna_metadata: dict[str, Any],
) -> list[ValidationIssue]:
    """Detect operational and genre-register contamination in chapter prose.

    The legacy patterns retain coverage for underscore-separated runtime
    tokens. The shared language-guard scanner adds profile-driven register
    checks so the consolidated gate cannot disagree with the critique loop.
    """
    if not chapter_text or not chapter_text.strip():
        return []
    issues: list[ValidationIssue] = []

    genre = str(
        project_dna_metadata.get("genre_primary")
        or project_dna_metadata.get("genre")
        or ""
    ).strip()
    if genre:
        from tools.novelkit_language_guard_tool import (
            blocking_violations,
            modern_register_allowed,
            scan,
        )

        allow_modern = modern_register_allowed(project_dna_metadata)
        violations = scan(
            chapter_text,
            genre,
            str(project_dna_metadata.get("genre_secondary") or "") or None,
            allow_modern_register=allow_modern,
        )
        profile_hits = [v for v in violations if v.source == "profile"]
        if profile_hits:
            blocked = blocking_violations(
                profile_hits,
                genre,
                allow_modern_register=allow_modern,
            )
            severity = "error" if blocked else "warning"
            issues.append(
                ValidationIssue(
                    code=f"{genre.upper()}_REGISTER_CONTAMINATION",
                    severity=severity,
                    message=(
                        f"{genre} register contamination in chapter "
                        f"{chapter_number}: "
                        + ", ".join(v.term for v in profile_hits[:5])
                    ),
                    path=f"chapters/chapter_{chapter_number:03d}.md",
                    details={
                        "violations": [v.to_dict() for v in profile_hits],
                        "total_count": sum(v.count for v in profile_hits),
                    },
                )
            )

    hits: list[str] = []
    for pattern in _OPERATIONAL_BANNED_PATTERNS:
        hits.extend(pattern.findall(chapter_text))
    if hits:
        unique_hits = sorted(set(hits))
        issues.append(
            ValidationIssue(
                code="LANGUAGE_CONTAMINATION",
                severity="error",
                message=(
                    f"Operational language detected in chapter {chapter_number}: "
                    f"{len(hits)} instance(s) — {', '.join(unique_hits[:5])}"
                ),
                path=f"chapters/chapter_{chapter_number:03d}.md",
                details={"hits": unique_hits, "total_count": len(hits)},
            )
        )
    return issues


def chapter_length_gate(
    novel_path: Path,
    chapter_number: int,
    chapter_text: str,
    review_text: str,
    project_dna_metadata: dict[str, Any],
) -> list[ValidationIssue]:
    """Verify chapter word count meets the 73%-of-target floor (ported)."""
    if not chapter_text or not chapter_text.strip():
        return []
    words = len(re.findall(r"\w+", chapter_text, flags=re.UNICODE))
    try:
        target = int(project_dna_metadata.get("target_words_per_chapter", 2500))
    except (TypeError, ValueError):
        target = 2500
    minimum = max(1, target * 22 // 30)
    if words < minimum:
        return [
            ValidationIssue(
                code="CHAPTER_TOO_SHORT",
                severity="error",
                message=(
                    f"Chapter {chapter_number} has {words} words, "
                    f"minimum is {minimum} (73% of target {target})"
                ),
                path=f"chapters/chapter_{chapter_number:03d}.md",
                details={"words": words, "minimum": minimum, "target": target},
            )
        ]
    return []


# ---- Genre gates (ported from gates/xianxia.py) --------------------------- #

_XIANXIA_CULTIVATION_KEYWORDS = (
    "kinh mạch", "đan điền", "chân nguyên", "thần thức", "đạo tâm", "linh khí",
    "tu luyện", "bế quan", "đột phá", "vận công", "dẫn khí", "chu thiên",
)


def xianxia_cultivation_gate(
    novel_path: Path,
    chapter_number: int,
    chapter_text: str,
    review_text: str,
    project_dna_metadata: dict[str, Any],
) -> list[ValidationIssue]:
    """Flag a substantial xianxia chapter with no cultivation signal (ported)."""
    if not chapter_text or len(chapter_text) <= 500:
        return []
    lower = chapter_text.lower()
    found = sum(1 for kw in _XIANXIA_CULTIVATION_KEYWORDS if kw in lower)
    if found == 0:
        return [
            ValidationIssue(
                code="XIANXIA_NO_CULTIVATION_SIGNAL",
                severity="warning",
                message=(
                    f"Chapter {chapter_number} has no cultivation keywords — "
                    "verify the cultivation-journey beat exists."
                ),
                details={"keywords_checked": len(_XIANXIA_CULTIVATION_KEYWORDS)},
            )
        ]
    return []


def _build_default_registry() -> GateRegistry:
    reg = GateRegistry()
    reg.register_common("language_guard", language_guard_gate)
    reg.register_common("chapter_length", chapter_length_gate)
    reg.register("xianxia", "cultivation_process", xianxia_cultivation_gate)
    return reg


#: Module-level singleton (mirrors gate_registry.get_registry()).
_REGISTRY = _build_default_registry()


def get_registry() -> GateRegistry:
    return _REGISTRY


# --------------------------------------------------------------------------- #
# evaluate() — the headline interface (design §Components #2)
# --------------------------------------------------------------------------- #


def evaluate(
    chapter: "str | Path | None" = None,
    review_file: "str | Path | None" = None,
    context: Optional[dict[str, Any]] = None,
) -> Verdict:
    """Evaluate a chapter against the review gate (design §Components #2).

    Parameters
    ----------
    chapter
        The chapter prose. May be a path to a ``.md`` file or the raw text.
    review_file
        The review document. May be a path or raw text (the reviewer's rubric
        + verdict). Drives the score + explicit verdict.
    context
        Optional dict carrying ``genre``, ``chapter_number``,
        ``project_dna`` / ``project_dna_metadata`` (for harem detection), and
        ``love_interests`` (list of female love-interest names).

    Returns
    -------
    Verdict
        ``outcome`` (done/soft_fail/hard_fail/blocked), ``score``,
        ``findings`` (gate ValidationIssues), and ``flags`` (e.g.
        ``EARLY_CHAPTER_SCORE_LIFT``, ``HAREM_VOICE_COLLAPSE``).

    The outcome follows the threshold table with explicit-verdict override
    (Property P2). Early Chapter Score Lift and Harem Progression add findings
    and flags but never lower the pass threshold.
    """
    context = context or {}
    chapter_text = _read_text_arg(chapter)
    review_text = _read_text_arg(review_file)

    genre = str(context.get("genre") or "").strip().lower()
    chapter_number = _coerce_int(context.get("chapter_number"))
    dna = (
        context.get("project_dna_metadata")
        or context.get("project_dna")
        or {}
    )
    if not isinstance(dna, dict):
        dna = {}
    else:
        dna = dict(dna)
    if genre:
        dna.setdefault("genre_primary", genre)
    novel_path = Path(context.get("novel_path") or ".")

    # 1) Parse review → score + explicit verdict, then map to outcome (P2).
    parsed = parse_review_text(review_text)
    outcome = score_to_outcome(parsed.score, parsed.verdict)

    findings: list[ValidationIssue] = []
    flags: list[str] = []

    # 2) Run the consolidated gate registry over the chapter prose.
    findings.extend(
        get_registry().execute_gates(
            genre=genre,
            novel_path=novel_path,
            chapter_number=chapter_number or 0,
            chapter_text=chapter_text,
            review_text=review_text,
            project_dna_metadata=dna,
        )
    )

    # 3) Early Chapter Score Lift (chapters 1-5): demand evidence, never lower
    #    the threshold (Requirement 9.3).
    if chapter_number is not None and 1 <= chapter_number <= EARLY_CHAPTER_MAX:
        flags.append("EARLY_CHAPTER_SCORE_LIFT")
        gaps = early_chapter_evidence_gaps(f"{review_text}\n{chapter_text}")
        if gaps:
            findings.append(
                ValidationIssue(
                    code="EARLY_CHAPTER_EVIDENCE_GAP",
                    severity="warning",
                    message=(
                        f"Early chapter {chapter_number}: missing on-page "
                        f"evidence for {', '.join(gaps)}. The bar stays at "
                        f"{REVIEW_PASS_SCORE}+ — raise the score with evidence, "
                        "do not soften the gate."
                    ),
                    details={"missing_evidence": gaps},
                )
            )

    # 4) Harem Progression — flag voice collapse when DNA declares harem
    #    (Requirement 9.4).
    if novel_declares_harem(dna):
        love_interests = [
            str(name) for name in (context.get("love_interests") or []) if name
        ]
        report = detect_harem_voice_collapse(chapter_text, love_interests)
        if report.collapsed:
            flags.append("HAREM_VOICE_COLLAPSE")
            findings.append(
                ValidationIssue(
                    code="HAREM_VOICE_COLLAPSE",
                    severity="warning",
                    message=(
                        "Harem voice collapse: multiple love-interest voices "
                        "share one fingerprint — "
                        + ", ".join(f"{a}~{b} ({s})" for a, b, s in report.pairs)
                    ),
                    details={
                        "pairs": [list(p) for p in report.pairs],
                        "speakers_analyzed": report.speakers_analyzed,
                    },
                )
            )

    # 5) A hard-block gate error escalates a passing outcome to hard_fail
    #    (the gate cannot let a contaminated/too-short chapter through).
    if outcome == OUTCOME_DONE and any(f.severity == "error" for f in findings):
        outcome = OUTCOME_HARD_FAIL

    return Verdict(outcome=outcome, score=parsed.score, findings=findings, flags=flags)


def _read_text_arg(value: "str | Path | None") -> str:
    """Resolve an argument that may be a path to a file or raw text."""
    if value is None:
        return ""
    if isinstance(value, Path):
        try:
            return value.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""
    text = str(value)
    # Treat a short single-line string ending in .md as a path.
    if "\n" not in text and text.strip().endswith(".md"):
        candidate = Path(text)
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return ""
    return text


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #

_GATE_TOOL_SCHEMA = {
    "name": "novelkit_gate",
    "description": (
        "Quality gate: score a chapter review against the 7-criteria rubric, "
        "apply thresholds with explicit-verdict override, run the consolidated "
        "gate registry, and surface Early Chapter Score Lift + Harem "
        "Progression flags. Returns a Verdict{outcome, score, findings, flags}."
    ),
    "input": {
        "type": "object",
        "properties": {
            "chapter": {
                "type": ["string", "null"],
                "description": "Chapter prose (raw text) or path to a .md file.",
            },
            "review_file": {
                "type": ["string", "null"],
                "description": "Review document (raw text) or path to a .md file.",
            },
            "context": {
                "type": "object",
                "description": (
                    "genre, chapter_number, project_dna_metadata, "
                    "love_interests, novel_path"
                ),
            },
        },
        "required": ["review_file"],
    },
    "output": {
        "type": "object",
        "properties": {
            "outcome": {
                "type": "string",
                "enum": [OUTCOME_DONE, OUTCOME_SOFT_FAIL, OUTCOME_HARD_FAIL, OUTCOME_BLOCKED],
            },
            "score": {"type": ["number", "null"]},
            "findings": {"type": "array"},
            "flags": {"type": "array"},
        },
        "required": ["outcome", "score", "findings", "flags"],
    },
}


def gate_tool(
    chapter: "str | Path | None" = None,
    review_file: "str | Path | None" = None,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stateless tool entrypoint: ``(chapter, review_file, context) -> Verdict dict``."""
    return evaluate(chapter, review_file, context).to_dict()


# Self-register at import time (Requirement 6.2 — self-registering tool).
registry.register(
    "novelkit_gate",
    gate_tool,
    schema=_GATE_TOOL_SCHEMA,
    module=__name__,
)
