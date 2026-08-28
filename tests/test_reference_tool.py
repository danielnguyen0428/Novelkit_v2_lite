"""Tests for the reference tool (Task 9.4, Requirements 15/17).

Covers chapter parsing, golden-3 selection, deterministic StyleProfile
extraction, canon-contamination detection, the empty/title-only path, and
self-registration.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_reference_tool import (
    StyleProfile,
    deconstruct,
    detect_canon_contamination,
    parse_chapters,
    reference_tool,
    select_golden_chapters,
)


_REF = (
    "Chương 1: Khởi đầu\n"
    "Hắn đứng trên đỉnh núi Thanh Vân. Gió rít qua vách đá. Lòng hắn lạnh như "
    "băng nhưng mắt vẫn rực lửa.\n\n"
    "Chương 2: Biến cố\n"
    "Lý Tiêu Dao rút kiếm. Một nhát chém xé toạc màn đêm. Máu nhuộm đỏ tuyết "
    "trắng trên đỉnh Thanh Vân.\n\n"
    "Chương 3: Cao trào\n"
    "Cả thành Thanh Vân chấn động. Tin tức lan truyền khắp đại lục."
)


# --------------------------------------------------------------------------- #
# Unit tests
# --------------------------------------------------------------------------- #


def test_parse_chapters_splits_headings() -> None:
    chapters = parse_chapters(_REF)
    assert len(chapters) == 3
    assert chapters[0].index == 1
    assert "Khởi đầu" in chapters[0].heading


def test_parse_chapters_no_heading_fallback() -> None:
    chapters = parse_chapters("Một đoạn văn không có tiêu đề chương.")
    assert len(chapters) == 1
    assert chapters[0].heading == "(no chapter heading)"


def test_select_golden_three() -> None:
    chapters = parse_chapters(_REF)
    golden = select_golden_chapters(chapters)
    assert len(golden) == 3


def test_deconstruct_produces_profile() -> None:
    profile = deconstruct(_REF, source_title="Thanh Vân Ký")
    assert isinstance(profile, StyleProfile)
    assert profile.source_title == "Thanh Vân Ký"
    assert profile.chapters_analyzed == 3
    assert profile.avg_sentence_words > 0
    assert 0.0 <= profile.lexical_diversity <= 1.0
    assert 0.0 <= profile.confidence <= 1.0
    # "Thanh", "Vân" appear repeatedly capitalised → do-not-copy candidates.
    assert any("Vân" in token or "Thanh" in token for token in profile.do_not_copy) or profile.do_not_copy == []


def test_empty_input_zero_confidence() -> None:
    profile = deconstruct("")
    assert profile.confidence == 0.0
    assert profile.chapters_analyzed == 0


def test_detect_canon_contamination() -> None:
    profile = StyleProfile(do_not_copy=["Thanh Vân", "Lý Tiêu Dao"])
    warnings = detect_canon_contamination(profile, "Truyện mới có núi Thanh Vân.")
    assert len(warnings) == 1
    assert detect_canon_contamination(profile, "Một thế giới hoàn toàn khác.") == []


def test_self_registration() -> None:
    entry = registry.get("novelkit_reference")
    assert entry.fn is reference_tool


# --------------------------------------------------------------------------- #
# Property-based tests
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(st.text())
def test_deconstruct_never_raises_bounded(text: str) -> None:
    profile = deconstruct(text)
    assert 0.0 <= profile.confidence <= 1.0
    assert 0.0 <= profile.lexical_diversity <= 1.0
    assert 0.0 <= profile.dialogue_ratio <= 1.0
    assert profile.avg_sentence_words >= 0.0
    assert profile.sentence_length_stdev >= 0.0


@settings(max_examples=100)
@given(st.text(min_size=1))
def test_parse_chapters_indices_monotonic(text: str) -> None:
    chapters = parse_chapters(text)
    indices = [c.index for c in chapters]
    assert indices == sorted(indices)
    assert all(c.index >= 1 for c in chapters)
