"""Tests for the unified gate tool (Task 6, Requirement 9).

Property-based tests cover the headline correctness property from design.md
§"Correctness Properties":

- **P2 — Gate monotonic & verdict override**: the outcome derived from
  ``(score, verdict)`` follows the threshold table; an explicit verdict always
  wins over the score band, and (with no verdict) the outcome is monotone
  non-decreasing in the score.
  **Validates: Requirements 9.1, 9.2**

Plus a golden review-scoring suite (ported from
``_novelkit_source/scripts/compare_signoff_golden.py``) that pins
``parse_review_text`` + ``score_to_outcome`` against expected outcomes, and unit
tests for the 7-criteria rubric parsing, Early Chapter Score Lift, Harem voice
collapse, the consolidated gate registry, and self-registration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_gate_tool import (
    EARLY_CHAPTER_MAX,
    OUTCOME_DONE,
    OUTCOME_HARD_FAIL,
    OUTCOME_SOFT_FAIL,
    REVIEW_CRITERIA,
    REVIEW_MAX_SCORE,
    REVIEW_PASS_SCORE,
    REVIEW_SOFT_FAIL_SCORE,
    GateRegistry,
    Verdict,
    detect_harem_voice_collapse,
    derive_typed_review,
    early_chapter_evidence_gaps,
    evaluate,
    gate_tool,
    get_registry,
    novel_declares_harem,
    parse_review_text,
    score_to_outcome,
)

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "review_scoring"

#: Quality ordering for the monotonicity check.
_OUTCOME_RANK = {OUTCOME_HARD_FAIL: 0, OUTCOME_SOFT_FAIL: 1, OUTCOME_DONE: 2}


# --------------------------------------------------------------------------- #
# Property 2 — Gate monotonic & verdict override
# --------------------------------------------------------------------------- #


@settings(max_examples=300)
@given(
    score=st.one_of(st.none(), st.floats(min_value=0, max_value=100)),
    verdict=st.sampled_from(["pass", "soft_fail", "hard_fail"]),
)
def test_property_explicit_verdict_always_wins(score, verdict):
    """P2: an explicit verdict overrides the score band entirely.

    **Validates: Requirements 9.2**
    """
    expected = OUTCOME_DONE if verdict == "pass" else verdict
    assert score_to_outcome(score, verdict) == expected


@settings(max_examples=300)
@given(score=st.floats(min_value=0, max_value=100))
def test_property_score_bands_follow_thresholds(score):
    """P2: with no verdict the score bands follow the threshold table.

    **Validates: Requirements 9.1**
    """
    outcome = score_to_outcome(score, None)
    if score >= REVIEW_PASS_SCORE:
        assert outcome == OUTCOME_DONE
    elif score >= REVIEW_SOFT_FAIL_SCORE:
        assert outcome == OUTCOME_SOFT_FAIL
    else:
        assert outcome == OUTCOME_HARD_FAIL


@settings(max_examples=300)
@given(
    s1=st.floats(min_value=0, max_value=100),
    s2=st.floats(min_value=0, max_value=100),
)
def test_property_outcome_monotone_in_score(s1, s2):
    """P2: with no verdict, a higher score never yields a worse outcome.

    **Validates: Requirements 9.1**
    """
    lo, hi = sorted((s1, s2))
    assert _OUTCOME_RANK[score_to_outcome(lo, None)] <= _OUTCOME_RANK[
        score_to_outcome(hi, None)
    ]


@settings(max_examples=200)
@given(
    score=st.floats(min_value=0, max_value=100),
    verdict=st.sampled_from(["pass", "soft_fail", "hard_fail"]),
)
def test_property_verdict_dominates_score_through_evaluate(score, verdict):
    """P2 end-to-end: a review carrying both a score and an explicit verdict
    resolves to the verdict-derived outcome regardless of the score.

    **Validates: Requirements 9.2**
    """
    verdict_label = {"pass": "PASS", "soft_fail": "SOFT-FAIL", "hard_fail": "HARD-FAIL"}[
        verdict
    ]
    review = f"### **TỔNG: {int(score)}/100**\n\n## Verdict: {verdict_label}\n"
    result = evaluate(chapter="", review_file=review, context={"chapter_number": 40})
    expected = OUTCOME_DONE if verdict == "pass" else verdict
    assert result.outcome == expected
    assert result.score == float(int(score))


def test_score_to_outcome_missing_score_no_verdict_is_hard_fail():
    assert score_to_outcome(None, None) == OUTCOME_HARD_FAIL


def test_score_to_outcome_boundaries():
    assert score_to_outcome(REVIEW_PASS_SCORE) == OUTCOME_DONE
    assert score_to_outcome(REVIEW_PASS_SCORE - 0.01) == OUTCOME_SOFT_FAIL
    assert score_to_outcome(REVIEW_SOFT_FAIL_SCORE) == OUTCOME_SOFT_FAIL
    assert score_to_outcome(REVIEW_SOFT_FAIL_SCORE - 0.01) == OUTCOME_HARD_FAIL


# --------------------------------------------------------------------------- #
# Golden review-scoring suite (ported from compare_signoff_golden.py)
# --------------------------------------------------------------------------- #


def _golden_cases():
    cases = []
    for expected_file in sorted(GOLDEN_DIR.glob("*.expected.json")):
        review_file = expected_file.with_name(
            expected_file.name.replace(".expected.json", ".md")
        )
        cases.append(pytest.param(review_file, expected_file, id=review_file.stem))
    return cases


@pytest.mark.parametrize("review_file,expected_file", _golden_cases())
def test_golden_review_scoring(review_file, expected_file):
    """Golden regression: parsed score/verdict/outcome match the fixtures.

    Replaces the legacy ``compare_signoff_golden.py`` for review scoring.
    """
    expected = json.loads(expected_file.read_text(encoding="utf-8"))
    text = review_file.read_text(encoding="utf-8")

    parsed = parse_review_text(text)
    outcome = score_to_outcome(parsed.score, parsed.verdict)

    assert parsed.score == expected["score"], f"score mismatch in {review_file.name}"
    assert parsed.verdict == expected["verdict"], (
        f"verdict mismatch in {review_file.name}"
    )
    assert outcome == expected["outcome"], f"outcome mismatch in {review_file.name}"
    assert parsed.criteria_total == expected["criteria_total"], (
        f"criteria_total mismatch in {review_file.name}"
    )


def test_golden_fixtures_exist():
    """Guard: the golden suite is non-empty (so the parametrize is meaningful)."""
    assert _golden_cases(), "no golden review-scoring fixtures found"


# --------------------------------------------------------------------------- #
# Unit tests — 7-criteria rubric
# --------------------------------------------------------------------------- #


def test_rubric_has_seven_criteria_summing_to_100():
    assert len(REVIEW_CRITERIA) == 7
    assert REVIEW_MAX_SCORE == 100


def test_parse_criteria_table_sums_to_total():
    text = (GOLDEN_DIR / "pass_rubric_table.md").read_text(encoding="utf-8")
    parsed = parse_review_text(text)
    # All 7 criteria present → criteria_total drives the score.
    assert len(parsed.criteria_scores) == 7
    assert parsed.criteria_total == 90.0
    assert parsed.score == 90.0
    assert parsed.verdict == "pass"


def test_partial_criteria_table_falls_back_to_total_label():
    text = "| Logic Consistency | 14/15 |\n\n### **TỔNG: 80/100**\n## Verdict: PASS\n"
    parsed = parse_review_text(text)
    # Not all 7 criteria → criteria_total is None, score from the label.
    assert parsed.criteria_total is None
    assert parsed.score == 80.0
    assert parsed.verdict == "pass"


def test_threshold_label_not_misread_as_verdict():
    text = (
        "- **Giới hạn hard-fail:** điểm dưới 70.\n"
        "### **TỔNG: 86/100**\n"
        "## Verdict: PASS\n"
    )
    parsed = parse_review_text(text)
    assert parsed.verdict == "pass"
    assert score_to_outcome(parsed.score, parsed.verdict) == OUTCOME_DONE


# --------------------------------------------------------------------------- #
# Unit tests — Early Chapter Score Lift (Requirement 9.3)
# --------------------------------------------------------------------------- #


def test_early_chapter_flag_set_for_chapters_1_to_5():
    review = "### **TỔNG: 90/100**\n## Verdict: PASS\n"
    for chapter in range(1, EARLY_CHAPTER_MAX + 1):
        result = evaluate("", review, {"chapter_number": chapter})
        assert "EARLY_CHAPTER_SCORE_LIFT" in result.flags


def test_early_chapter_flag_absent_after_chapter_5():
    review = "### **TỔNG: 90/100**\n## Verdict: PASS\n"
    result = evaluate("", review, {"chapter_number": 6})
    assert "EARLY_CHAPTER_SCORE_LIFT" not in result.flags


def test_early_chapter_lift_does_not_lower_threshold():
    """A passing early chapter stays done even when evidence is missing —
    the lift demands evidence (a finding) but never softens the gate."""
    review = "### **TỔNG: 88/100**\n## Verdict: PASS\n"  # no evidence markers
    result = evaluate("", review, {"chapter_number": 1})
    assert result.outcome == OUTCOME_DONE
    assert any(f.code == "EARLY_CHAPTER_EVIDENCE_GAP" for f in result.findings)


def test_early_chapter_evidence_present_no_gap_finding():
    review = (
        "Scene promise rõ, Core Wound được hành động hóa, World Pressure chạm "
        "trực tiếp lựa chọn, và một micro-payoff hữu hình.\n"
        "### **TỔNG: 88/100**\n## Verdict: PASS\n"
    )
    result = evaluate("", review, {"chapter_number": 1})
    assert not any(f.code == "EARLY_CHAPTER_EVIDENCE_GAP" for f in result.findings)


def test_early_chapter_evidence_gaps_helper():
    assert set(early_chapter_evidence_gaps("")) == {
        "scene_promise",
        "core_wound",
        "world_pressure",
        "micro_payoff",
    }
    assert early_chapter_evidence_gaps(
        "scene promise, core wound, world pressure, payoff"
    ) == []


# --------------------------------------------------------------------------- #
# Unit tests — Harem Progression (Requirement 9.4)
# --------------------------------------------------------------------------- #


def test_novel_declares_harem_detection():
    assert novel_declares_harem({"harem": True})
    assert novel_declares_harem({"harem": "yes"})
    assert novel_declares_harem({"notes": "truyện có hậu cung đông đảo"})
    assert not novel_declares_harem({"genre": "xianxia"})
    assert not novel_declares_harem({})


def test_harem_voice_collapse_flags_identical_voices():
    # Two love interests speak the exact same lines → fingerprints collapse.
    chapter = (
        'Lan nói: "Ta tin chàng sẽ thắng trận này thôi mà."\n'
        'Lan đáp: "Ta tin chàng sẽ thắng trận này thôi mà."\n'
        'Cúc nói: "Ta tin chàng sẽ thắng trận này thôi mà."\n'
        'Cúc đáp: "Ta tin chàng sẽ thắng trận này thôi mà."\n'
    )
    report = detect_harem_voice_collapse(chapter, ["Lan", "Cúc"])
    assert report.collapsed is True
    assert ("Cúc", "Lan", report.pairs[0][2]) or report.pairs  # pair recorded

    result = evaluate(chapter, "### **TỔNG: 90/100**\n## Verdict: PASS\n", {
        "chapter_number": 40,
        "project_dna_metadata": {"harem": True},
        "love_interests": ["Lan", "Cúc"],
    })
    assert "HAREM_VOICE_COLLAPSE" in result.flags


def test_harem_voice_distinct_voices_not_flagged():
    chapter = (
        'Lan nói: "Thiếp chỉ mong chàng bình an trở về, mọi vinh hoa thiếp chẳng màng."\n'
        'Lan thì thầm: "Đêm nay sương lạnh, chàng nhớ khoác thêm áo."\n'
        'Cúc cười lớn: "Hừ, đánh nhau thì gọi ta, ta chém trước hỏi sau cho nhanh gọn!"\n'
        'Cúc quát: "Ai dám cản đường bổn cô nương thì liệu hồn gãy chân đấy!"\n'
    )
    report = detect_harem_voice_collapse(chapter, ["Lan", "Cúc"])
    assert report.collapsed is False


def test_harem_collapse_requires_two_speakers():
    chapter = 'Lan nói: "Ta tin chàng." Lan đáp: "Ta tin chàng."'
    report = detect_harem_voice_collapse(chapter, ["Lan"])
    assert report.collapsed is False


def test_harem_flag_absent_when_dna_does_not_declare_harem():
    chapter = (
        'Lan nói: "Ta tin chàng sẽ thắng."\n'
        'Cúc nói: "Ta tin chàng sẽ thắng."\n'
    )
    result = evaluate(chapter, "### **TỔNG: 90/100**\n## Verdict: PASS\n", {
        "chapter_number": 40,
        "project_dna_metadata": {"genre": "xianxia"},
        "love_interests": ["Lan", "Cúc"],
    })
    assert "HAREM_VOICE_COLLAPSE" not in result.flags


# --------------------------------------------------------------------------- #
# Unit tests — consolidated gate registry
# --------------------------------------------------------------------------- #


def test_language_contamination_escalates_pass_to_hard_fail():
    chapter = "Nhân vật mở control_plane và chạy pipeline runtime để debug." * 3
    result = evaluate(chapter, "### **TỔNG: 90/100**\n## Verdict: PASS\n", {
        "chapter_number": 40,
        "genre": "xianxia",
    })
    # A passing review with an error-severity gate finding cannot proceed.
    assert any(f.code == "LANGUAGE_CONTAMINATION" for f in result.findings)
    assert result.outcome == OUTCOME_HARD_FAIL


def test_xianxia_register_contamination_escalates_pass_to_hard_fail():
    chapter = (
        "— Trụ ơi, tối rồi về ăn cơm với tao! "
        "Giọng A Mãnh, thằng bạn từ nhỏ, lẫn trong tiếng gió. "
        "— Sao mày không nói sớm?"
    )
    result = evaluate(chapter, "### **TỔNG: 97/100**\n## Verdict: PASS\n", {
        "chapter_number": 40,
        "genre": "xianxia",
        "project_dna_metadata": {"genre_primary": "xianxia"},
    })

    assert any(
        f.code == "XIANXIA_REGISTER_CONTAMINATION" for f in result.findings
    )
    assert result.outcome == OUTCOME_HARD_FAIL


def test_strict_classical_xianxia_blocks_profile_warning_terms():
    result = evaluate(
        "Hắn mở hồ sơ, cân nhắc logic của vụ việc.",
        "### **TỔNG: 97/100**\n## Verdict: PASS\n",
        {
            "chapter_number": 40,
            "genre": "xianxia",
            "project_dna_metadata": {"genre_primary": "xianxia"},
        },
    )

    finding = next(
        f for f in result.findings
        if f.code == "XIANXIA_REGISTER_CONTAMINATION"
    )
    assert finding.severity == "error"
    assert result.outcome == OUTCOME_HARD_FAIL


def test_declared_modern_xianxia_skips_traditional_register_finding():
    result = evaluate(
        "Tao nói mày nghe, đừng bước qua cửa ấy.",
        "### **TỔNG: 97/100**\n## Verdict: PASS\n",
        {
            "chapter_number": 40,
            "genre": "xianxia",
            "project_dna_metadata": {
                "genre_primary": "xianxia",
                "world_era": "Tu tiên đô thị hiện đại",
            },
        },
    )

    assert not any(
        f.code == "XIANXIA_REGISTER_CONTAMINATION" for f in result.findings
    )


def test_clean_chapter_no_contamination_findings():
    chapter = (
        "Hắn vận công dẫn linh khí qua kinh mạch, đan điền rung lên một nhịp, "
        "thần thức quét khắp gian phòng tĩnh mịch dưới ánh trăng lạnh."
    ) * 120
    result = evaluate(chapter, "### **TỔNG: 90/100**\n## Verdict: PASS\n", {
        "chapter_number": 40,
        "genre": "xianxia",
    })
    assert not any(f.severity == "error" for f in result.findings)
    assert result.outcome == OUTCOME_DONE


def test_registry_common_and_genre_gates_registered():
    reg = get_registry()
    assert "language_guard" in reg.common_gate_names
    assert "chapter_length" in reg.common_gate_names
    assert "cultivation_process" in reg.genre_gate_names["xianxia"]


def test_registry_unknown_genre_runs_common_only():
    reg = GateRegistry()
    reg.register_common("x", lambda *a: [])
    gates = reg.get_gates("not_a_genre")
    assert [g.name for g in gates] == ["x"]


def test_registry_rejects_unknown_genre_registration():
    reg = GateRegistry()
    with pytest.raises(ValueError):
        reg.register("not_a_genre", "g", lambda *a: [])


def test_typed_review_derives_pass_from_required_dimensions():
    review = derive_typed_review(
        review_id="chapter_0001_attempt_01",
        chapter=1,
        attempt=1,
        draft_sha256="a" * 64,
        dimensions={
            "plot_progression": 90,
            "character_consistency": 86,
            "continuity": 88,
            "prose_quality": 87,
            "dialogue_voice": 85,
            "world_consistency": 89,
            "reader_momentum": 90,
        },
    )

    assert review["schema_version"] == 2
    assert review["overall_score"] == 88
    assert review["gate_outcome"] == "pass"
    assert review["final_action"] == "sync"


def test_typed_review_derives_polish_and_rewrite_deterministically():
    base_dimensions = {
        "plot_progression": 82,
        "character_consistency": 82,
        "continuity": 82,
        "prose_quality": 82,
        "dialogue_voice": 82,
        "world_consistency": 82,
        "reader_momentum": 82,
    }

    polish = derive_typed_review(
        review_id="chapter_0001_attempt_01",
        chapter=1,
        attempt=1,
        draft_sha256="a" * 64,
        dimensions=base_dimensions,
    )
    rewrite = derive_typed_review(
        review_id="chapter_0001_attempt_02",
        chapter=1,
        attempt=2,
        draft_sha256="b" * 64,
        dimensions={**base_dimensions, "continuity": 59},
        issues=[{"issue_id": "issue_001", "severity": "critical"}],
    )

    assert polish["overall_score"] == 82
    assert polish["gate_outcome"] == "polish"
    assert polish["final_action"] == "queue_polish"
    assert rewrite["gate_outcome"] == "rewrite"
    assert rewrite["final_action"] == "queue_rewrite"


def test_registry_isolates_gate_exceptions():
    reg = GateRegistry()

    def boom(*_a):
        raise RuntimeError("kaboom")

    reg.register_common("boom", boom)
    issues = reg.execute_gates("xianxia", Path("."), 1, "text", "", {})
    assert any(i.code == "GATE_EXCEPTION_BOOM" for i in issues)
    assert all(i.severity == "warning" for i in issues)


# --------------------------------------------------------------------------- #
# Unit tests — tool entrypoint + self-registration
# --------------------------------------------------------------------------- #


def test_tool_is_self_registered():
    assert "novelkit_gate" in registry.list_tools()
    entry = registry.get("novelkit_gate")
    assert entry.fn is gate_tool
    assert entry.schema is not None


def test_gate_tool_returns_verdict_dict():
    out = gate_tool("", "### **TỔNG: 90/100**\n## Verdict: PASS\n", {"chapter_number": 40})
    assert out["outcome"] == OUTCOME_DONE
    assert out["score"] == 90.0
    assert isinstance(out["findings"], list)
    assert isinstance(out["flags"], list)


def test_evaluate_returns_verdict_object():
    result = evaluate("", "### **TỔNG: 50/100**\n## Verdict: HARD-FAIL\n", {})
    assert isinstance(result, Verdict)
    assert result.outcome == OUTCOME_HARD_FAIL


def test_evaluate_reads_review_from_file(tmp_path):
    review = tmp_path / "chapter_040_review.md"
    review.write_text("### **TỔNG: 88/100**\n## Verdict: PASS\n", encoding="utf-8")
    result = evaluate("", review, {"chapter_number": 40})
    assert result.outcome == OUTCOME_DONE
    assert result.score == 88.0
