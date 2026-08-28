"""NovelKit reference tool — deconstruct a reference text into a StyleProfile.

Phase 3 of the migration (Task 9.4). Extracts the *deterministic* craft of the
legacy ``reference_deconstructor.py`` and repackages it as a self-registering
Hermes Custom Tool.

The legacy module routed most of its analysis through LLM calls (Gemini) plus
its own provider/timeout wiring. Per the migration contract, that LLM wiring is
**dropped** (it belongs to Hermes provider resolution); what survives is the
deterministic, measurable analysis that yields a reusable **StyleProfile** for
Author Style / ``style_vault`` seeding:

- chapter parsing (``第N章`` / ``Chapter N`` / ``Ch N`` / ``Chương N``),
- golden-3 chapter selection,
- measurable prose-style metrics (sentence/paragraph length, burstiness,
  dialogue ratio, lexical diversity, signature openers, top vocabulary),
- canon-contamination detection (a fact appearing verbatim in derived text).

``StyleProfile`` carries *patterns, not facts* — the same anti-contamination
principle as the source: patterns transfer, plot facts do not. The module is
dependency-free (stdlib only) plus the local ``tools.registry`` shim.

Design references: design.md §"Components and Interfaces" #8
(``deconstruct(reference_text) -> StyleProfile``).
Requirements 15 (author-style prose floor), 17 (multi-genre).
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from tools import registry

#: Minimum tokens before lexical metrics are considered meaningful.
_MIN_TOKENS_FOR_CONFIDENCE = 80

_STOPWORDS = {
    "cua", "của", "mot", "một", "nhung", "nhưng", "khong", "không",
    "trong", "ngoai", "ngoài", "duoc", "được", "hắn", "nàng", "người",
    "chương", "rồi", "này", "đã", "các", "với", "cũng", "thì", "là",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ChapterContent:
    """One chapter slice produced by :func:`parse_chapters`."""

    index: int
    heading: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StyleProfile:
    """Reusable author-style fingerprint extracted from a reference text.

    Carries measurable *patterns* (not source facts) suitable for seeding an
    Author Style profile / ``style_vault`` entry.

    Attributes:
        source_title: optional display title echoed from the caller.
        chapters_analyzed: how many chapter slices contributed.
        avg_sentence_words / sentence_length_stdev: pacing + *burstiness*
            (higher stdev → more human-like sentence variety).
        avg_paragraph_words: paragraph density.
        dialogue_ratio: fraction of prose carried by dialogue lines.
        lexical_diversity: type/token ratio over content words.
        signature_openers: most common paragraph-opening words (voice tics).
        top_terms: dominant content vocabulary (motifs, not plot facts).
        do_not_copy: capitalised proper-noun-like tokens to avoid borrowing.
        confidence: 0..1 heuristic — low when the sample is too small.
    """

    source_title: str = ""
    chapters_analyzed: int = 0
    avg_sentence_words: float = 0.0
    sentence_length_stdev: float = 0.0
    avg_paragraph_words: float = 0.0
    dialogue_ratio: float = 0.0
    lexical_diversity: float = 0.0
    signature_openers: list[str] = field(default_factory=list)
    top_terms: list[str] = field(default_factory=list)
    do_not_copy: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Combined chapter-heading regex (ported from reference_deconstructor.py).
_CHAPTER_HEADING_RE = re.compile(
    r"""
    ^[ \t]*
    (?:\#{1,3}[ \t]+)?
    (?:
        第[ \t]*[\d一二三四五六七八九十百千零〇两兩]+[ \t]*章[^\n]*
        |
        Chapter[ \t]+\d+[^\n]*
        |
        Ch\.?[ \t]*\d+[^\n]*
        |
        Chương[ \t]+\d+[^\n]*
    )
    """,
    re.MULTILINE | re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Chapter parsing (ported from reference_deconstructor.py)
# ---------------------------------------------------------------------------


def parse_chapters(text: str) -> list[ChapterContent]:
    """Split source text into :class:`ChapterContent` chunks.

    No detectable boundaries → one synthetic chapter with the full text.
    """
    if not text:
        return []
    matches = list(_CHAPTER_HEADING_RE.finditer(text))
    if not matches:
        body = text.strip()
        if not body:
            return []
        return [ChapterContent(index=1, heading="(no chapter heading)", body=body)]

    chapters: list[ChapterContent] = []
    for i, match in enumerate(matches):
        heading = match.group(0).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        chapters.append(ChapterContent(index=i + 1, heading=heading, body=body))
    return chapters


def select_golden_chapters(chapters: list[ChapterContent]) -> list[ChapterContent]:
    """Pick the chapter 1 / middle / last triad ("golden 3")."""
    if not chapters:
        return []
    if len(chapters) <= 3:
        return list(chapters)
    middle = len(chapters) // 2
    last = len(chapters) - 1
    return [chapters[0], chapters[middle], chapters[last]]


# ---------------------------------------------------------------------------
# Style feature extraction (deterministic)
# ---------------------------------------------------------------------------


def _strip_markdown(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith(("#", "```", "<!--", "|"))
    ]
    return "\n".join(lines)


def _sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?。！？…])\s+", _strip_markdown(text))
        if sentence.strip()
    ]


def _tokens(text: str) -> list[str]:
    return [
        token.casefold()
        for token in re.findall(r"[\wÀ-ỹ]{3,}", _strip_markdown(text), flags=re.UNICODE)
        if token.casefold() not in _STOPWORDS
    ]


def _paragraphs(text: str) -> list[str]:
    return [line.strip() for line in _strip_markdown(text).splitlines() if line.strip()]


def _dialogue_ratio(text: str) -> float:
    stripped = _strip_markdown(text)
    if not stripped.strip():
        return 0.0
    dialogue_chars = 0
    for line in stripped.splitlines():
        clean = line.strip()
        if clean.startswith(("-", "“", '"', "—")):
            dialogue_chars += len(clean)
    return round(dialogue_chars / max(1, len(stripped)), 4)


def _signature_openers(paragraphs: list[str], top: int = 8) -> list[str]:
    """Most common paragraph-opening words — a cheap voice fingerprint."""
    openers: Counter[str] = Counter()
    for para in paragraphs:
        words = re.findall(r"[\wÀ-ỹ]+", para, flags=re.UNICODE)
        if words:
            openers[words[0].casefold()] += 1
    return [word for word, _ in openers.most_common(top)]


def _do_not_copy(text: str, top: int = 15) -> list[str]:
    """Proper-noun-like tokens (capitalised, not sentence-initial) to avoid."""
    stripped = _strip_markdown(text)
    candidates: Counter[str] = Counter()
    for match in re.finditer(r"(?<![.!?。！？…]\s)(?<!^)\b([A-ZÀ-Ỹ][a-zà-ỹ]{2,})", stripped):
        token = match.group(1)
        if token.casefold() in _STOPWORDS:
            continue
        candidates[token] += 1
    return [token for token, count in candidates.most_common(top) if count >= 2]


# ---------------------------------------------------------------------------
# Public deconstruction entry point
# ---------------------------------------------------------------------------


def deconstruct(reference_text: str, *, source_title: str = "") -> StyleProfile:
    """Deconstruct a reference text into a :class:`StyleProfile`.

    Deterministic and side-effect-free. Title-only / empty input yields an
    all-zero profile with ``confidence == 0.0`` so callers can branch on it
    instead of relying on exceptions.
    """
    if not reference_text or not reference_text.strip():
        return StyleProfile(source_title=source_title)

    chapters = parse_chapters(reference_text)
    golden = select_golden_chapters(chapters)
    sample_text = "\n\n".join(ch.body for ch in golden) or reference_text

    sentences = _sentences(sample_text)
    sentence_lengths = [
        len(re.findall(r"\w+", s, flags=re.UNICODE)) for s in sentences
    ]
    paragraphs = _paragraphs(sample_text)
    tokens = _tokens(sample_text)

    avg_sentence_words = (
        round(sum(sentence_lengths) / len(sentence_lengths), 2)
        if sentence_lengths
        else 0.0
    )
    sentence_stdev = (
        round(statistics.pstdev(sentence_lengths), 2)
        if len(sentence_lengths) > 1
        else 0.0
    )
    avg_paragraph_words = round(len(tokens) / max(1, len(paragraphs)), 2)
    lexical_diversity = round(len(set(tokens)) / max(1, len(tokens)), 4)
    top_terms = [term for term, _ in Counter(tokens).most_common(25)]

    confidence = round(min(1.0, len(tokens) / max(1, _MIN_TOKENS_FOR_CONFIDENCE)), 4)

    return StyleProfile(
        source_title=source_title,
        chapters_analyzed=len(golden),
        avg_sentence_words=avg_sentence_words,
        sentence_length_stdev=sentence_stdev,
        avg_paragraph_words=avg_paragraph_words,
        dialogue_ratio=_dialogue_ratio(sample_text),
        lexical_diversity=lexical_diversity,
        signature_openers=_signature_openers(paragraphs),
        top_terms=top_terms,
        do_not_copy=_do_not_copy(sample_text),
        confidence=confidence,
    )


def detect_canon_contamination(profile: StyleProfile, derived_text: str) -> list[str]:
    """Warn when a profile's do-not-copy fact appears verbatim in derived text.

    Patterns transfer, facts do not — this guards style_vault/Author Style
    seeds from accidentally inheriting a source's proper nouns.
    """
    if not derived_text or not profile.do_not_copy:
        return []
    haystack = derived_text.lower()
    warnings: list[str] = []
    for fact in profile.do_not_copy:
        if fact and fact.strip().lower() in haystack:
            warnings.append(f"derived text copies source proper noun {fact!r}")
    return warnings


# ---------------------------------------------------------------------------
# Tool entrypoint + self-registration (Requirement 6.2)
# ---------------------------------------------------------------------------

_REFERENCE_TOOL_SCHEMA = {
    "name": "novelkit_reference",
    "description": (
        "Reference deconstructor: extract a deterministic StyleProfile "
        "(sentence/paragraph metrics, burstiness, dialogue ratio, lexical "
        "diversity, signature openers, vocabulary, do-not-copy nouns) from a "
        "reference text for Author Style / style_vault seeding."
    ),
    "input": {
        "type": "object",
        "properties": {
            "reference_text": {"type": "string"},
            "source_title": {"type": "string"},
        },
        "required": ["reference_text"],
    },
    "output": {"type": "object"},
}


def reference_tool(
    reference_text: str, *, source_title: str = ""
) -> dict[str, Any]:
    """Stateless tool entrypoint — wraps :func:`deconstruct`."""
    return deconstruct(reference_text, source_title=source_title).to_dict()


def _resolve_input_text(
    reference_text: Optional[str], text_path: Optional[str]
) -> str:
    """Prefer an inline excerpt; otherwise read a UTF-8 file path."""
    if reference_text:
        return reference_text
    if text_path:
        path = Path(text_path)
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return ""
    return ""


registry.register(
    "novelkit_reference",
    reference_tool,
    schema=_REFERENCE_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "ChapterContent",
    "StyleProfile",
    "parse_chapters",
    "select_golden_chapters",
    "deconstruct",
    "detect_canon_contamination",
    "reference_tool",
]
