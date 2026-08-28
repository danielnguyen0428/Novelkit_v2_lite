"""Tests for the cool-point tool (Task 9.1, Requirements 15/16).

Unit tests cover paragraph classification, block clustering, the release-layer
filter, reaction-tier counting, density, and self-registration. Property-based
tests assert structural invariants that must hold for any chapter text.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_cool_point_tool import (
    LAYERS,
    analyze,
    classify_paragraph,
    cool_point_tool,
    detect_cool_points,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

_FULL_BLOCK = (
    "Không khí ngột ngạt, sát khí lạnh gáy bao trùm. Toàn trường im lặng.\n\n"
    "Hắn xuất chiêu, một quyền bùng nổ, phá vỡ trận pháp.\n\n"
    "Mọi người trợn mắt, không thể tin nổi. Cả thành xôn xao, tin tức lan "
    "truyền khắp nơi.\n\n"
    "Yên lặng trở lại, một lát sau ai cũng rời đi."
)


# --------------------------------------------------------------------------- #
# Unit tests
# --------------------------------------------------------------------------- #


def test_classify_paragraph_layers() -> None:
    assert classify_paragraph("Không khí ngột ngạt, sát khí lạnh gáy.")[0] == "setup"
    assert classify_paragraph("Hắn xuất chiêu, một quyền bùng nổ.")[0] == "release"
    assert classify_paragraph("")[0] is None
    assert classify_paragraph("một câu trung tính không marker")[0] is None


def test_detect_cool_points_full_block() -> None:
    report = detect_cool_points(_FULL_BLOCK, 1)
    assert len(report.blocks) == 1
    block = report.blocks[0]
    assert block.setup_words > 0
    assert block.release_words > 0
    # tier 3 markers ("cả thành", "tin tức lan", "khắp nơi") fired
    assert block.reaction_tier_count == 3


def test_block_requires_release_layer() -> None:
    # Setup + reaction only, no release → not a cool point.
    text = (
        "Không khí ngột ngạt, căng thẳng nín thở.\n\n"
        "Mọi người kinh ngạc, há hốc miệng."
    )
    report = detect_cool_points(text, 2)
    assert report.blocks == []


def test_analyze_density_and_gaps() -> None:
    result = analyze(_FULL_BLOCK, 1, genre="xianxia")
    assert result["count"] == 1
    assert result["genre"] == "xianxia"
    assert result["density"] > 0
    assert "gaps" in result


def test_empty_chapter_is_zero() -> None:
    result = analyze("", 5)
    assert result["count"] == 0
    assert result["density"] == 0.0
    assert result["cool_points"] == []


def test_self_registration() -> None:
    entry = registry.get("novelkit_cool_point")
    assert entry.fn is cool_point_tool
    assert entry.schema is not None


# --------------------------------------------------------------------------- #
# Property-based tests
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(st.text(), st.integers(min_value=1, max_value=999))
def test_detect_never_raises_and_reaction_tier_bounded(text: str, chapter: int) -> None:
    report = detect_cool_points(text, chapter)
    assert report.chapter == chapter
    for block in report.blocks:
        # reaction tier count is always clamped to 0..3
        assert 0 <= block.reaction_tier_count <= 3
        # every retained block has a release layer
        assert block.release_words > 0
        assert block.pacing_ratio >= 0.0


@settings(max_examples=100)
@given(st.text())
def test_classify_scores_cover_all_layers(paragraph: str) -> None:
    layer, scores = classify_paragraph(paragraph)
    assert set(scores) == set(LAYERS)
    if layer is not None:
        assert layer in LAYERS
