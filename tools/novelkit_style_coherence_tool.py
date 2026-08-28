"""NovelKit style-coherence tool — periodic style drift audit.

Phase 3 of the migration (Task 9.3). Extracts the style-coherence audit from
the legacy ``style_coherence.py`` and repackages it as a self-registering
Hermes Custom Tool. It measures a chapter's prose style (sentence/paragraph
length, dialogue ratio, lexical diversity, top vocabulary) and compares it
against a baseline (typically the opening chapters) to flag drift before it
costs reader trust over a 300+ chapter run.

Reports are written to ``reviews/style_coherence/chapter_NNN_style_audit.{json,md}``.
The module is dependency-free (stdlib only) plus the local ``tools.registry``
shim.

Design references: design.md §"Components and Interfaces" #7
(``audit(novel_path, baseline_chapters, current_chapter) -> DriftReport``).
Requirements 11.4 (style coherence audit), 16 (anti-AI-detection proxy).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools import registry

#: Style audit cadence (ported from style_coherence.py).
STYLE_AUDIT_INTERVAL_CHAPTERS = 10

_STOPWORDS = {
    "cua", "của", "mot", "một", "nhung", "nhưng", "khong", "không",
    "trong", "ngoai", "ngoài", "duoc", "được", "hắn", "nàng", "người",
    "chương",
}


def style_audit_due(
    chapter: int, *, interval: int = STYLE_AUDIT_INTERVAL_CHAPTERS
) -> bool:
    """True when chapter > 3 and on the audit cadence (every 10th by default)."""
    return chapter > 3 and interval > 0 and chapter % interval == 0


# ---------------------------------------------------------------------------
# Text feature extraction (ported from style_coherence.py)
# ---------------------------------------------------------------------------


def _read_chapter(novel_path: Path, chapter: int) -> str:
    path = novel_path / "chapters" / f"chapter_{chapter:03d}.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


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
        for token in re.findall(
            r"[\wÀ-ỹ]{3,}", _strip_markdown(text), flags=re.UNICODE
        )
        if token.casefold() not in _STOPWORDS
    ]


def _dialogue_ratio(text: str) -> float:
    stripped = _strip_markdown(text)
    if not stripped.strip():
        return 0.0
    dialogue_chars = 0
    for line in stripped.splitlines():
        clean = line.strip()
        if clean.startswith(("-", "“", '"')):
            dialogue_chars += len(clean)
    return round(dialogue_chars / max(1, len(stripped)), 4)


def style_metrics(text: str) -> dict[str, Any]:
    """Compute the style metric vector for a block of prose."""
    sentences = _sentences(text)
    words_per_sentence = [
        len(re.findall(r"\w+", sentence, flags=re.UNICODE)) for sentence in sentences
    ]
    paragraphs = [line for line in _strip_markdown(text).splitlines() if line.strip()]
    tokens = _tokens(text)
    top_terms = [term for term, _ in Counter(tokens).most_common(25)]
    return {
        "sentence_count": len(sentences),
        "avg_sentence_words": round(
            sum(words_per_sentence) / max(1, len(words_per_sentence)), 2
        ),
        "avg_paragraph_words": round(len(tokens) / max(1, len(paragraphs)), 2),
        "dialogue_ratio": _dialogue_ratio(text),
        "lexical_diversity": round(len(set(tokens)) / max(1, len(tokens)), 4),
        "top_terms": top_terms,
    }


def _relative_delta(baseline: float, current: float) -> float:
    if baseline == 0:
        return 0.0 if current == 0 else 1.0
    return abs(current - baseline) / abs(baseline)


def _vocabulary_overlap(baseline_terms: list[str], current_terms: list[str]) -> float:
    baseline = set(baseline_terms[:20])
    current = set(current_terms[:20])
    if not baseline:
        return 1.0
    return round(len(baseline.intersection(current)) / len(baseline), 4)


# ---------------------------------------------------------------------------
# Staleness / repetition across chapters (anti-"mòn văn phong")
# ---------------------------------------------------------------------------

#: How many preceding chapters to compare against for repetition.
REPETITION_LOOKBACK_CHAPTERS = 5
#: Opening-line Jaccard similarity at/above this is flagged as a repeated open.
REPEATED_OPENING_THRESHOLD = 0.6
#: Share of the lookback window an opening n-gram must recur in to be "stale".
STALE_OPENING_NGRAM_SHARE = 0.6
#: Length (in tokens) of the opening n-gram fingerprint.
_OPENING_NGRAM_LEN = 4


def _opening_line(text: str) -> str:
    """The first non-empty prose sentence of a chapter (markdown stripped)."""
    stripped = _strip_markdown(text)
    for sentence in _sentences(stripped):
        if sentence.strip():
            return sentence.strip()
    return ""


def _opening_ngram(text: str) -> str:
    """A normalised first-N-token fingerprint of a chapter's opening."""
    tokens = _tokens(_opening_line(text))[:_OPENING_NGRAM_LEN]
    return " ".join(tokens)


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(_tokens(a)), set(_tokens(b))
    if not sa or not sb:
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 4)


def build_repetition_report(
    novel_path: Path,
    chapter: int,
    *,
    lookback: int = REPETITION_LOOKBACK_CHAPTERS,
) -> dict[str, Any]:
    """Detect prose staleness: chapter openings that echo recent chapters.

    Complements drift detection (which catches a chapter diverging *too much*)
    by catching the opposite failure mode — chapters converging on the same
    opening line / phrase, the "mòn văn phong" an AI factory drifts into. Looks
    back over the previous ``lookback`` chapters. Report-only.
    """
    current_open = _opening_line(_read_chapter(novel_path, chapter))
    if not current_open:
        return {"status": "skipped", "reason": "missing_current_chapter"}

    prior_chapters = [c for c in range(max(1, chapter - lookback), chapter)]
    prior_opens = {c: _opening_line(_read_chapter(novel_path, c)) for c in prior_chapters}
    prior_opens = {c: o for c, o in prior_opens.items() if o}

    flags: dict[str, Any] = {}

    # 1) Near-duplicate opening lines vs each recent chapter.
    similar = []
    for c, prev_open in prior_opens.items():
        sim = _jaccard(current_open, prev_open)
        if sim >= REPEATED_OPENING_THRESHOLD:
            similar.append({"chapter": c, "similarity": sim})
    if similar:
        flags["repeated_opening_line"] = {
            "current_opening": current_open,
            "matches": sorted(similar, key=lambda m: -m["similarity"]),
            "threshold": REPEATED_OPENING_THRESHOLD,
        }

    # 2) Opening n-gram that recurs across most of the window.
    current_ngram = _opening_ngram(_read_chapter(novel_path, chapter))
    if current_ngram and prior_opens:
        prior_ngrams = [_opening_ngram(_read_chapter(novel_path, c)) for c in prior_opens]
        recurrences = sum(1 for ng in prior_ngrams if ng and ng == current_ngram)
        share = round(recurrences / len(prior_ngrams), 4)
        if share >= STALE_OPENING_NGRAM_SHARE:
            flags["stale_opening_pattern"] = {
                "opening_ngram": current_ngram,
                "recurrence_share": share,
                "window": sorted(prior_opens),
                "threshold": STALE_OPENING_NGRAM_SHARE,
            }

    return {
        "status": "warning" if flags else "ok",
        "chapter": chapter,
        "lookback": lookback,
        "flags": flags,
    }


# ---------------------------------------------------------------------------
# Report building + writing
# ---------------------------------------------------------------------------


def build_style_coherence_report(
    novel_path: Path,
    chapter: int,
    *,
    baseline_chapters: tuple[int, ...] = (1, 2, 3),
) -> dict[str, Any]:
    """Compare ``chapter`` style against the baseline chapters; flag drift."""
    current_text = _read_chapter(novel_path, chapter)
    baseline_text = "\n\n".join(
        _read_chapter(novel_path, item) for item in baseline_chapters
    )
    if not current_text.strip() or not baseline_text.strip():
        return {
            "status": "skipped",
            "chapter": chapter,
            "reason": "missing_current_or_baseline_chapters",
        }

    baseline = style_metrics(baseline_text)
    current = style_metrics(current_text)
    drift: dict[str, Any] = {}
    for key, threshold in (
        ("avg_sentence_words", 0.35),
        ("avg_paragraph_words", 0.45),
        ("dialogue_ratio", 0.25),
        ("lexical_diversity", 0.35),
    ):
        delta = _relative_delta(float(baseline[key]), float(current[key]))
        if delta > threshold:
            drift[key] = {
                "baseline": baseline[key],
                "current": current[key],
                "relative_delta": round(delta, 4),
                "threshold": threshold,
            }

    overlap = _vocabulary_overlap(baseline["top_terms"], current["top_terms"])
    if overlap < 0.2:
        drift["top_vocabulary_overlap"] = {
            "baseline_top_terms": baseline["top_terms"][:10],
            "current_top_terms": current["top_terms"][:10],
            "overlap": overlap,
            "threshold": 0.2,
        }

    repetition = build_repetition_report(novel_path, chapter)
    has_repetition = repetition.get("status") == "warning"

    return {
        "status": "warning" if (drift or has_repetition) else "ok",
        "chapter": chapter,
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_chapters": list(baseline_chapters),
        "baseline": baseline,
        "current": current,
        "drift": drift,
        "repetition": repetition,
    }


def write_style_coherence_report(
    novel_path: Path, report: dict[str, Any]
) -> dict[str, Path]:
    """Write the JSON + markdown audit to ``reviews/style_coherence/``."""
    chapter = int(report.get("chapter") or 0)
    report_dir = novel_path / "reviews" / "style_coherence"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"chapter_{chapter:03d}_style_audit.json"
    markdown_path = report_dir / f"chapter_{chapter:03d}_style_audit.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    drift_lines = []
    for key, value in sorted((report.get("drift") or {}).items()):
        drift_lines.append(f"- `{key}`: {value}")
    if not drift_lines:
        drift_lines.append("- Không phát hiện drift vượt ngưỡng.")

    repetition = report.get("repetition") or {}
    rep_lines = []
    for key, value in sorted((repetition.get("flags") or {}).items()):
        rep_lines.append(f"- `{key}`: {value}")
    if not rep_lines:
        rep_lines.append("- Không phát hiện lặp/mòn văn phong vượt ngưỡng.")

    markdown_path.write_text(
        "\n".join(
            [
                f"# Style Coherence Audit - chapter_{chapter:03d}",
                "",
                f"- Status: `{report.get('status')}`",
                f"- Baseline chapters: `{report.get('baseline_chapters')}`",
                "",
                "## Drift",
                *drift_lines,
                "",
                "## Lặp / Mòn văn phong",
                *rep_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": markdown_path}


def audit(
    novel_path: str,
    current_chapter: int,
    baseline_chapters: tuple[int, ...] = (1, 2, 3),
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Tool interface (design #7): build the drift report and optionally persist."""
    path = Path(novel_path)
    report = build_style_coherence_report(
        path, current_chapter, baseline_chapters=tuple(baseline_chapters)
    )
    if write and report.get("status") != "skipped":
        written = write_style_coherence_report(path, report)
        report = dict(report)
        report["written"] = {k: str(v) for k, v in written.items()}
    return report


# ---------------------------------------------------------------------------
# Tool entrypoint + self-registration (Requirement 6.2)
# ---------------------------------------------------------------------------

_STYLE_COHERENCE_TOOL_SCHEMA = {
    "name": "novelkit_style_coherence",
    "description": (
        "Style coherence audit: compare a chapter's prose metrics (sentence / "
        "paragraph length, dialogue ratio, lexical diversity, vocabulary) to a "
        "baseline and flag drift; writes reviews/style_coherence/* reports."
    ),
    "input": {
        "type": "object",
        "properties": {
            "novel_path": {"type": "string"},
            "current_chapter": {"type": "integer"},
            "baseline_chapters": {"type": "array", "items": {"type": "integer"}},
            "write": {"type": "boolean"},
        },
        "required": ["novel_path", "current_chapter"],
    },
    "output": {"type": "object"},
}


def style_coherence_tool(
    novel_path: str,
    current_chapter: int,
    *,
    baseline_chapters: tuple[int, ...] = (1, 2, 3),
    write: bool = True,
) -> dict[str, Any]:
    """Stateless tool entrypoint — wraps :func:`audit`."""
    return audit(
        novel_path, current_chapter, tuple(baseline_chapters), write=write
    )


registry.register(
    "novelkit_style_coherence",
    style_coherence_tool,
    schema=_STYLE_COHERENCE_TOOL_SCHEMA,
    module=__name__,
)


__all__ = [
    "STYLE_AUDIT_INTERVAL_CHAPTERS",
    "REPETITION_LOOKBACK_CHAPTERS",
    "style_audit_due",
    "style_metrics",
    "build_repetition_report",
    "build_style_coherence_report",
    "write_style_coherence_report",
    "audit",
    "style_coherence_tool",
]


# ---------------------------------------------------------------------------
# Long-form GA: per-chapter style-stats self-mirror + repeated-sentence guard
# (Req 7; Property P19). style_stats lives under logs/ (derivative — it must
# never rank as canon, unlike the memory/ prefix).
# ---------------------------------------------------------------------------

STYLE_STATS_REL = "logs/style_stats.json"

#: Exemplar bank of the writer's OWN highest-reviewed prose, injected back into
#: the writer envelope as positive few-shot (learn from your best), complementing
#: style_stats which only teaches what to avoid. Derivative — never canon (P19).
STYLE_EXEMPLARS_REL = "logs/style_exemplars.json"
#: A chapter must score at/above this (gate ``overall_score``) to be an exemplar.
EXEMPLAR_MIN_SCORE = 85
#: Cap on exemplars kept (most recent high scorers win) to bound the word budget.
EXEMPLAR_MAX_ITEMS = 3
#: Max characters of prose kept per exemplar excerpt.
EXEMPLAR_EXCERPT_CHARS = 600

#: Edit-derived style signal (Tier 1, strongest signal): a diff of the writer's
#: original draft vs the user-edited canon. Sentences the user DELETED are tics
#: to avoid; sentences the user ADDED are preferred models. Derivative — never
#: canon (P19); injected as context only, never auto-written into PROJECT_DNA.
STYLE_EDITS_REL = "logs/style_edits.json"
#: Cap on user-edit signals kept per side (added/removed) to bound word budget.
EDIT_MAX_ITEMS = 5
#: A draft/canon sentence shorter than this is ignored (noise: headings, tags).
EDIT_MIN_SENTENCE_LEN = 20

#: Tier 2 cross-novel "style lab": a GLOBAL craft profile distilled from many
#: novels' highest-scored chapters. To prevent one novel's voice/world leaking
#: into another, it stores ONLY numeric craft metrics (sentence length, dialogue
#: ratio, lexical diversity) — never prose text, names, or world terms. Lives in
#: the user's home dir, so it is strictly opt-in (``style_global`` flag).
GLOBAL_STYLE_DIR = Path.home() / ".hermes" / "style_lab"
GLOBAL_PROFILE_PATH = GLOBAL_STYLE_DIR / "global_profile.json"
#: Numeric craft metrics carried into the global profile (text-free by design).
_GLOBAL_METRIC_KEYS = (
    "avg_sentence_words",
    "avg_paragraph_words",
    "dialogue_ratio",
    "lexical_diversity",
)

_CORRECTIVE_RE = re.compile(r"không\s+phải\b.{0,40}?\bmà\b", re.IGNORECASE | re.DOTALL)
_TIMING_RE = re.compile(
    r"\b(?:vài|mấy|dăm|một|hai|ba)\s*(?:tức|khắc|canh|hơi thở|nhịp thở)\b",
    re.IGNORECASE,
)
_SIMILE_RE = re.compile(r"\bnhư\b", re.IGNORECASE)


def _first_token(sentence: str) -> str:
    toks = _tokens(sentence)
    return toks[0] if toks else ""


def _last_token(sentence: str) -> str:
    toks = _tokens(sentence)
    return toks[-1] if toks else ""


def build_style_stats(
    novel_path: "str | Path", current_chapter: int, *, window: int = 10
) -> dict[str, Any]:
    """Accumulate the writer's own stylistic tics over the last ``window``
    chapters and persist them to ``logs/style_stats.json`` (Req 7.1).

    Deterministic over the chapter window (P19); the result is injected back
    into the writer envelope so it can actively suppress its high-frequency
    patterns. Derivative artifact — never canon.
    """
    root = Path(novel_path)
    start = max(1, current_chapter - window + 1)
    openers: Counter = Counter()
    closers: Counter = Counter()
    total = corrective = timing = simile = 0
    for c in range(start, current_chapter + 1):
        text = _read_chapter(root, c)
        if not text:
            continue
        for sentence in _sentences(text):
            total += 1
            ft = _first_token(sentence)
            if ft:
                openers[ft] += 1
            lt = _last_token(sentence)
            if lt:
                closers[lt] += 1
            if _CORRECTIVE_RE.search(sentence):
                corrective += 1
            if _TIMING_RE.search(sentence):
                timing += 1
            if _SIMILE_RE.search(sentence):
                simile += 1
    stats = {
        "window": window,
        "through_chapter": current_chapter,
        "sentence_count": total,
        "top_openers": openers.most_common(8),
        "top_closers": closers.most_common(8),
        "corrective_sentence_rate": round(corrective / max(1, total), 4),
        "timing_quantifier_rate": round(timing / max(1, total), 4),
        "simile_rate": round(simile / max(1, total), 4),
    }
    out = root / STYLE_STATS_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(stats, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return stats


def _review_score(novel_path: Path, chapter: int) -> "float | None":
    """Read the canon-gate ``overall_score`` for ``chapter`` from its typed
    review sidecar. Returns ``None`` when the review is missing/unparseable."""
    path = novel_path / "reviews" / f"chapter_{chapter:04d}_review.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    score = data.get("overall_score")
    return float(score) if isinstance(score, (int, float)) else None


def _exemplar_excerpt(text: str, *, max_chars: int = EXEMPLAR_EXCERPT_CHARS) -> str:
    """A clean opening excerpt of a chapter's prose (markdown stripped), cut on a
    sentence boundary so the writer sees whole sentences as a positive model."""
    picked: list[str] = []
    used = 0
    for sentence in _sentences(text):
        if used + len(sentence) > max_chars and picked:
            break
        picked.append(sentence)
        used += len(sentence) + 1
    return " ".join(picked).strip()


def _passes_language_guard(novel_path: Path, text: str) -> bool:
    """Prevent contaminated prose from becoming a positive style exemplar."""
    from tools.novelkit_language_guard_tool import (
        blocking_violations,
        scan,
        workspace_guard_context,
    )

    primary, secondary, allow_modern = workspace_guard_context(novel_path)
    violations = scan(
        text,
        primary,
        secondary,
        allow_modern_register=allow_modern,
    )
    return not blocking_violations(
        violations,
        primary,
        allow_modern_register=allow_modern,
    )


def build_exemplar_bank(
    novel_path: "str | Path",
    current_chapter: int,
    *,
    window: int = 10,
    min_score: int = EXEMPLAR_MIN_SCORE,
    max_items: int = EXEMPLAR_MAX_ITEMS,
) -> dict[str, Any]:
    """Collect the writer's OWN highest-reviewed prose over the last ``window``
    chapters and persist it to ``logs/style_exemplars.json`` (per-novel Tier 1).

    Where :func:`build_style_stats` teaches the writer what tics to *avoid*, this
    teaches it what to *emulate*: chapters whose canon-gate ``overall_score`` is
    at/above ``min_score`` become positive few-shot excerpts injected back into
    the writer envelope. Deterministic over the chapter window (P19). Derivative
    artifact — never canon.
    """
    root = Path(novel_path)
    start = max(1, current_chapter - window + 1)
    candidates: list[dict[str, Any]] = []
    for c in range(start, current_chapter + 1):
        score = _review_score(root, c)
        if score is None or score < min_score:
            continue
        text = _read_chapter(root, c)
        if text and not _passes_language_guard(root, text):
            continue
        excerpt = _exemplar_excerpt(text) if text else ""
        if not excerpt:
            continue
        candidates.append({"chapter": c, "score": score, "excerpt": excerpt})
    # Highest score wins; recency (higher chapter) breaks ties. Bound the count
    # to keep the injected word budget small.
    candidates.sort(key=lambda e: (e["score"], e["chapter"]), reverse=True)
    exemplars = candidates[:max_items]
    bank = {
        "window": window,
        "through_chapter": current_chapter,
        "min_score": min_score,
        "exemplars": exemplars,
    }
    out = root / STYLE_EXEMPLARS_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(bank, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return bank


def _significant_sentences(text: str, *, min_len: int) -> list[str]:
    """Prose sentences long enough to carry a style signal (markdown stripped)."""
    return [s for s in _sentences(text) if len(s) >= min_len]


def _diff_chapter_edit(
    novel_path: Path, chapter: int, *, min_len: int
) -> "dict[str, Any] | None":
    """Diff one chapter's ORIGINAL draft against its (possibly user-edited) canon.

    A sentence in the draft but gone from canon is a tic the user removed; a
    sentence in canon but not in the draft is prose the user added/rewrote.
    Returns ``None`` when the pair is missing or byte-identical (no user edit).
    """
    draft_path = novel_path / "drafts" / f"chapter_{chapter:04d}.md"
    canon_path = novel_path / "chapters" / f"chapter_{chapter:03d}.md"
    if not draft_path.exists() or not canon_path.exists():
        return None
    draft_text = draft_path.read_text(encoding="utf-8")
    canon_text = canon_path.read_text(encoding="utf-8")
    if draft_text == canon_text:
        return None
    draft_sentences = _significant_sentences(draft_text, min_len=min_len)
    canon_sentences = _significant_sentences(canon_text, min_len=min_len)
    canon_set = set(canon_sentences)
    draft_set = set(draft_sentences)
    removed = [s for s in draft_sentences if s not in canon_set]
    added = [s for s in canon_sentences if s not in draft_set]
    if not removed and not added:
        return None
    return {"chapter": chapter, "removed_by_user": removed, "added_by_user": added}


def build_edit_signal(
    novel_path: "str | Path",
    current_chapter: int,
    *,
    window: int = 10,
    max_items: int = EDIT_MAX_ITEMS,
    min_len: int = EDIT_MIN_SENTENCE_LEN,
) -> "dict[str, Any] | None":
    """Scan the last ``window`` chapters for USER EDITS (canon that diverged from
    the writer's original draft) and persist the aggregate style signal to
    ``logs/style_edits.json`` (Tier 1, per-novel).

    This is the strongest learning signal: what a human actually changed. Sync
    copies draft→canon, so the just-synced chapter is always identical; real
    edits happen *afterwards* (via the webapp artifact editor), which is why this
    scans the PRIOR window rather than only ``current_chapter``. Removed
    sentences are tics to avoid; added sentences are preferred models. Injected
    back into the writer envelope as context only — never auto-written into
    ``PROJECT_DNA`` (that would bump the rules digest and force re-validation),
    keeping this a pure derivative artifact (P19).

    Returns ``None`` (and writes no artifact) when no edited chapter is found.
    """
    root = Path(novel_path)
    start = max(1, current_chapter - window + 1)
    removed: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    edited_chapters: list[int] = []
    # Most-recent edits first so the bounded lists keep the freshest signal.
    for c in range(current_chapter, start - 1, -1):
        diff = _diff_chapter_edit(root, c, min_len=min_len)
        if diff is None:
            continue
        edited_chapters.append(c)
        removed += [{"chapter": c, "sentence": s} for s in diff["removed_by_user"]]
        added += [{"chapter": c, "sentence": s} for s in diff["added_by_user"]]

    if not edited_chapters:
        return None

    signal = {
        "window": window,
        "through_chapter": current_chapter,
        "edited_chapters": sorted(edited_chapters),
        "removed_by_user": removed[:max_items],   # tics to avoid
        "added_by_user": added[:max_items],       # preferred models
    }
    out = root / STYLE_EDITS_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(signal, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return signal


# ---------------------------------------------------------------------------
# Tier 2: cross-novel global craft profile ("style lab", opt-in style_global)
# ---------------------------------------------------------------------------


def _running_mean(prev_mean: float, prev_n: int, value: float) -> float:
    """Incremental mean so re-distilling never re-reads other novels."""
    return (prev_mean * prev_n + value) / (prev_n + 1)


def _load_global_profile() -> dict[str, Any]:
    try:
        data = json.loads(GLOBAL_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def distill_global_profile(
    novel_path: "str | Path",
    current_chapter: int,
    *,
    window: int = 10,
    min_score: int = EXEMPLAR_MIN_SCORE,
) -> "dict[str, Any] | None":
    """Fold this novel's high-scored chapters into the GLOBAL craft profile at
    ``~/.hermes/style_lab/global_profile.json`` (Tier 2, cross-novel).

    Deliberately stores ONLY numeric craft metrics (mean sentence length,
    dialogue ratio, lexical diversity) averaged over the novel's chapters scoring
    at/above ``min_score`` — never prose, names, or world terms — so technique
    accumulates across novels without any one novel's voice/world bleeding into
    another. Idempotent per novel: each novel contributes at most one sample
    (keyed by novel path), so re-running does not double-count. Strictly opt-in
    (caller gates on the ``style_global`` flag). Derivative — never canon.

    Returns the updated profile, or ``None`` when the novel has no qualifying
    high-scored chapters yet.
    """
    root = Path(novel_path)
    start = max(1, current_chapter - window + 1)
    samples: list[dict[str, float]] = []
    for c in range(start, current_chapter + 1):
        if (_review_score(root, c) or 0) < min_score:
            continue
        text = _read_chapter(root, c)
        if not text.strip():
            continue
        metrics = style_metrics(text)
        samples.append({k: float(metrics[k]) for k in _GLOBAL_METRIC_KEYS})
    if not samples:
        return None

    novel_metrics = {
        k: round(sum(s[k] for s in samples) / len(samples), 4)
        for k in _GLOBAL_METRIC_KEYS
    }

    profile = _load_global_profile()
    novels: dict[str, Any] = profile.get("novels", {})
    if not isinstance(novels, dict):
        novels = {}
    novel_key = str(root.resolve())
    novels[novel_key] = {
        "metrics": novel_metrics,
        "chapters_sampled": len(samples),
        "through_chapter": current_chapter,
    }

    # Global craft mean = simple mean across contributing novels (text-free).
    n = len(novels)
    aggregate = {
        k: round(sum(v["metrics"][k] for v in novels.values()) / n, 4)
        for k in _GLOBAL_METRIC_KEYS
    }
    updated = {
        "schema_version": 1,
        "novels_count": n,
        "craft_metrics": aggregate,
        "novels": novels,
    }
    GLOBAL_STYLE_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_PROFILE_PATH.write_text(
        json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def load_global_craft_metrics() -> "dict[str, Any] | None":
    """Read the aggregate global craft metrics for injection into the writer
    envelope (Tier 2). Returns ``None`` when no global profile exists yet."""
    profile = _load_global_profile()
    metrics = profile.get("craft_metrics")
    if not isinstance(metrics, dict) or not metrics:
        return None
    return {
        "craft_metrics": metrics,
        "novels_count": profile.get("novels_count"),
    }


def repeated_sentence_findings(
    draft_text: str,
    prev_texts: "list[str] | str | None",
    *,
    window: int = 3,
    repeat_max: int = 1,
    min_len: int = 40,
) -> list[dict[str, Any]]:
    """Flag verbatim cross-chapter sentence reuse ("复述", Req 7.3; P19).

    A draft sentence of at least ``min_len`` characters that appears verbatim in
    any of the previous ``window`` chapters is a repeat. When the number of such
    repeats reaches ``repeat_max`` (default 1 → any verbatim recap), a
    ``REPEATED_SENTENCE`` finding is returned (the self-check turns this into a
    soft-fail).
    """
    if isinstance(prev_texts, str):
        prev_list = [prev_texts]
    else:
        prev_list = list(prev_texts or [])
    prev_sentences: set[str] = set()
    for text in prev_list[-window:]:
        for sentence in _sentences(text or ""):
            s = sentence.strip()
            if len(s) >= min_len:
                prev_sentences.add(s)
    hits = [
        s.strip()
        for s in _sentences(draft_text or "")
        if len(s.strip()) >= min_len and s.strip() in prev_sentences
    ]
    if len(hits) < repeat_max:
        return []
    return [
        {
            "code": "REPEATED_SENTENCE",
            "severity": "soft_fail",
            "sentence": s,
            "message": "Câu lặp nguyên văn so với chương trước (复述).",
        }
        for s in hits
    ]
