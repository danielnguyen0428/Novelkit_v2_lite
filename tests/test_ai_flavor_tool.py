"""Tests for the anti-AI-detection tool (Task 8, Requirements 15/16).

The headline correctness property:

- **P9 — Anti-AI-flavor detection**: text containing a known AI-flavor pattern
  is always detected together with the corresponding ``fix_hint``; the
  human-like reference corpus never false-positives above the risk threshold.
  **Validates: Requirements 16.2**

Plus unit tests for the burstiness/repetition heuristics, the voice-fingerprint
collapse check (Requirement 16.4), the bounded/monotonic risk model, the
``detect`` contract shape, the tool entrypoint and self-registration.
"""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_ai_flavor_tool import (
    DIMENSIONS,
    RISK_THRESHOLD,
    AIFlavorResult,
    AIFlavorViolation,
    ai_flavor_tool,
    compute_risk_score,
    detect,
    detect_burstiness_issue,
    detect_repetition_issue,
    detect_voice_collapse,
    load_patterns,
    sentence_length_cv,
    voice_fingerprint,
)

# --------------------------------------------------------------------------- #
# Fixtures / corpus
# --------------------------------------------------------------------------- #

_CORPUS_PATH = Path(__file__).parent / "fixtures" / "ai_flavor_corpus.json"


def _load_corpus() -> dict:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


#: One single-match trigger snippet per known config pattern. Repeating a
#: snippet ``required_count`` times pushes the pattern over its threshold.
_TRIGGER_SNIPPETS: dict[str, str] = {
    "light_adverb_verb": "Hắn khẽ cười. ",
    "eye_expression_template": "Ánh mắt thoáng tối. ",
    "smile_not_reaching_eyes": "Nụ cười không chạm đến mắt. ",
    "four_stage_closure": "Vì mưa nên đường trơn kết quả xe ngã từ đó muộn giờ. ",
    "parallel_three_clause": "Nàng vừa cười vừa khóc vừa run. ",
    "dramatic_irony_hint": "Hắn đâu ngờ điều này. ",
    "uniform_pacing_marker": "Sau đó hắn đi. ",
    "felt_very_label": "Hắn cảm thấy rất vui. ",
    "heart_label": "Trong lòng dâng lên nỗi buồn. ",
    "post_dialogue_explanation": "Hắn nói vậy vì sợ. ",
    "info_dump_long_dialogue": '"' + ("a" * 230) + '" ',
    "self_explaining_motive": "Ý của hắn là tốt. ",
}


def _flatten_config() -> dict[str, dict]:
    """Map ``pattern_name -> conf`` across every dimension in the config."""
    flat: dict[str, dict] = {}
    config = load_patterns()
    for dim in DIMENSIONS:
        for name, conf in config.get(dim, {}).items():
            flat[name] = conf
    return flat


def _required_count(conf: dict) -> int:
    """Repetitions needed to exceed a pattern's threshold (window or total)."""
    if "max_occurrences_per_window" in conf:
        return int(conf["max_occurrences_per_window"]) + 1
    return int(conf.get("max_occurrences", 0)) + 1


_CONFIG = _flatten_config()
_PATTERN_NAMES = sorted(_CONFIG)


# --------------------------------------------------------------------------- #
# Property 9 — every known pattern is always detected with its fix_hint
# --------------------------------------------------------------------------- #


@settings(max_examples=120)
@given(
    pattern_name=st.sampled_from(_PATTERN_NAMES),
    extra=st.integers(min_value=0, max_value=6),
)
def test_property_known_pattern_always_detected_with_fix_hint(pattern_name, extra):
    """P9: any text carrying a known AI-flavor pattern (at/above its threshold)
    is detected, and the reported violation carries the config's fix_hint.

    **Validates: Requirements 16.2**
    """
    conf = _CONFIG[pattern_name]
    snippet = _TRIGGER_SNIPPETS[pattern_name]
    count = _required_count(conf) + extra
    text = snippet * count

    result = detect(text)
    matched = [v for v in result.violations if v.pattern == pattern_name]

    assert matched, f"pattern {pattern_name!r} not detected in {count} reps"
    expected_hint = str(conf.get("fix_hint", "")).strip()
    if expected_hint:
        assert all(v.fix_hint == expected_hint for v in matched)
        assert expected_hint in result.fix_hints
    # A detected known pattern always lifts the risk above zero.
    assert result.risk_score > 0.0


# --------------------------------------------------------------------------- #
# Property 9 — human-like corpus never false-positives above threshold
# --------------------------------------------------------------------------- #


def test_property_human_corpus_below_threshold():
    """P9 (no false positive): every human-like passage scores below the risk
    threshold and is not flagged ``requires_fix``.

    **Validates: Requirements 16.2**
    """
    corpus = _load_corpus()
    for passage in corpus["human_like"]:
        result = detect(passage["text"])
        assert result.risk_score < RISK_THRESHOLD, (
            f"{passage['id']} false-positive: risk={result.risk_score} "
            f"≥ threshold {RISK_THRESHOLD} (violations: "
            f"{[v.pattern for v in result.violations]})"
        )
        assert result.requires_fix is False


def test_property_ai_corpus_above_threshold():
    """P9 (detection): every AI-flavored passage scores at/above the threshold
    and is flagged ``requires_fix`` with at least one actionable fix_hint.

    **Validates: Requirements 16.2**
    """
    corpus = _load_corpus()
    for passage in corpus["ai_flavored"]:
        result = detect(passage["text"])
        assert result.risk_score >= RISK_THRESHOLD, (
            f"{passage['id']} under-detected: risk={result.risk_score} "
            f"< threshold {RISK_THRESHOLD}"
        )
        assert result.requires_fix is True
        assert result.fix_hints, f"{passage['id']} produced no fix hints"


def test_corpus_separation_margin():
    """Sanity: the highest human score stays strictly below the lowest AI score
    (the threshold sits in the gap), guarding against drift.
    """
    corpus = _load_corpus()
    human = [detect(p["text"]).risk_score for p in corpus["human_like"]]
    ai = [detect(p["text"]).risk_score for p in corpus["ai_flavored"]]
    assert max(human) < RISK_THRESHOLD <= min(ai)


# --------------------------------------------------------------------------- #
# Unit tests — detect() contract shape (design.md §Components #4)
# --------------------------------------------------------------------------- #


def test_detect_returns_contract_shape():
    result = detect("Một câu văn bình thường.")
    assert isinstance(result, AIFlavorResult)
    d = result.to_dict()
    for key in ("risk_score", "violations", "fix_hints", "requires_fix"):
        assert key in d
    assert isinstance(d["risk_score"], float)
    assert isinstance(d["violations"], list)
    assert isinstance(d["fix_hints"], list)


def test_detect_empty_text_is_zero_risk():
    for text in ("", "   ", "\n\n"):
        result = detect(text)
        assert result.risk_score == 0.0
        assert result.violations == []
        assert result.requires_fix is False


def test_fix_hints_are_deduplicated():
    # Three felt_very_label hits → one violation, one fix hint (not three).
    text = "Hắn cảm thấy rất vui. Cô cảm thấy rất buồn. Y cảm thấy rất sợ."
    result = detect(text)
    assert len(result.fix_hints) == len(set(result.fix_hints))


# --------------------------------------------------------------------------- #
# Unit tests — burstiness heuristic (Task 8.2)
# --------------------------------------------------------------------------- #


def test_burstiness_flags_uniform_sentences():
    # Eight sentences of near-identical length → low CV → flagged.
    uniform = " ".join(["Hắn đi tới cửa rồi nhìn ra sân vắng lặng."] * 8)
    issue = detect_burstiness_issue(uniform)
    assert issue is not None
    assert issue.pattern == "low_burstiness"


def test_burstiness_ignores_bursty_prose():
    bursty = (
        "Hắn dừng. Cánh cửa gỗ nặng nề từ từ hé mở để lộ một hành lang dài hun "
        "hút chìm trong bóng tối đặc quánh mùi ẩm mốc của thời gian. Hắn bước. "
        "Một tiếng động vang lên đâu đó rất xa, mơ hồ như tiếng thở dài của cả "
        "tòa lâu đài cổ. Im lặng. Rồi tiếng bước chân."
    )
    assert detect_burstiness_issue(bursty) is None


def test_sentence_length_cv_none_when_too_few():
    assert sentence_length_cv("Một câu. Hai câu.") is None


# --------------------------------------------------------------------------- #
# Unit tests — repetition heuristic (Task 8.2)
# --------------------------------------------------------------------------- #


def test_repetition_flags_cloned_openers():
    text = (
        "Hắn lặng lẽ nhìn trời. Hắn lặng lẽ bước đi. Hắn lặng lẽ ngồi xuống. "
        "Hắn lặng lẽ thở dài. Hắn lặng lẽ quay lưng. Hắn lặng lẽ rời đi. "
        "Hắn lặng lẽ khép cửa."
    )
    issue = detect_repetition_issue(text)
    assert issue is not None
    assert issue.pattern == "repeated_opener"


def test_repetition_ignores_varied_openers():
    text = (
        "Mưa rơi trên mái ngói. Gió luồn qua khe cửa. Một con mèo nhảy xuống "
        "thềm. Lão già ho khan. Đèn dầu chợt tắt. Bóng tối nuốt chửng căn phòng. "
        "Ngoài kia, sấm rền từng hồi."
    )
    assert detect_repetition_issue(text) is None


# --------------------------------------------------------------------------- #
# Unit tests — voice fingerprint / collapse (Requirement 16.4)
# --------------------------------------------------------------------------- #


def test_voice_collapse_flags_identical_voices():
    # Two characters given the same dialogue → identical fingerprints.
    line = (
        "Ta nghĩ rằng chuyện này cần được cân nhắc thật kỹ trước khi quyết định "
        "bất cứ điều gì quan trọng."
    )
    violations = detect_voice_collapse({"A": line, "B": line})
    assert violations
    assert violations[0].pattern == "voice_collapse"
    assert violations[0].severity == "high"


def test_voice_distinct_voices_not_flagged():
    voices = {
        "Lão tướng": (
            "Đánh! Không lùi! Ai sợ chết thì cút khỏi hàng ngũ của ta ngay lập "
            "tức cho khuất mắt!"
        ),
        "Thư sinh": (
            "Tại hạ trộm nghĩ... có lẽ ta nên xem lại địa hình một chút, e rằng "
            "hành quân vội vàng sẽ chuốc lấy hiểm họa khôn lường chăng?"
        ),
    }
    assert detect_voice_collapse(voices) == []


def test_voice_fingerprint_empty_is_empty():
    assert voice_fingerprint("") == {}


def test_detect_uses_voices_when_provided():
    line = (
        "Ta cho rằng điều này hoàn toàn hợp lý và không có gì phải bàn cãi thêm "
        "về nó nữa cả."
    )
    result = detect("Một đoạn văn trung tính.", voices={"A": line, "B": line})
    assert any(v.pattern == "voice_collapse" for v in result.violations)


# --------------------------------------------------------------------------- #
# Unit tests — risk model
# --------------------------------------------------------------------------- #


def test_risk_score_bounded():
    many = [
        AIFlavorViolation("vocabulary", f"p{i}", "high", "0-1", "x", "fix", 9)
        for i in range(50)
    ]
    score = compute_risk_score(many)
    assert 0.0 <= score <= 100.0


def test_risk_score_monotonic_in_violations():
    base = [AIFlavorViolation("vocabulary", "p", "high", "0-1", "x", "fix", 1)]
    more = base + [
        AIFlavorViolation("syntax", "q", "medium", "0-1", "x", "fix", 1)
    ]
    assert compute_risk_score(more) >= compute_risk_score(base)


def test_risk_score_empty_is_zero():
    assert compute_risk_score([]) == 0.0


# --------------------------------------------------------------------------- #
# Unit tests — tool entrypoint + self-registration (Requirement 6.2)
# --------------------------------------------------------------------------- #


def test_tool_is_self_registered():
    assert "novelkit_ai_flavor" in registry.list_tools()
    entry = registry.get("novelkit_ai_flavor")
    assert entry.fn is ai_flavor_tool
    assert entry.schema is not None


def test_tool_entrypoint_returns_dict():
    out = ai_flavor_tool("Hắn cảm thấy rất vui. Cô cảm thấy rất buồn. Y cảm thấy rất sợ.")
    assert isinstance(out, dict)
    assert "risk_score" in out
    assert out["requires_fix"] in (True, False)


def test_tool_entrypoint_accepts_voices():
    line = (
        "Ta nghĩ rằng việc này cần được cân nhắc kỹ lưỡng trước khi đưa ra bất "
        "kỳ quyết định nào."
    )
    out = ai_flavor_tool("Đoạn văn.", voices={"A": line, "B": line})
    assert any(v["pattern"] == "voice_collapse" for v in out["violations"])
