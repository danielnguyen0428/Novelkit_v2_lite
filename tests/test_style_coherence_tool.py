"""Tests for the style-coherence tool (Task 9.3, Requirements 11.4/16).

Covers the audit cadence, metric extraction, drift detection vs a baseline,
report writing to reviews/style_coherence/*, the skipped path, and
self-registration.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_style_coherence_tool import (
    audit,
    build_style_coherence_report,
    style_audit_due,
    style_coherence_tool,
    style_metrics,
)


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


def _write_chapter(novel: Path, chapter: int, text: str) -> None:
    chapters = novel / "chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / f"chapter_{chapter:03d}.md").write_text(text, encoding="utf-8")


_BASE = (
    "Hắn bước vào sảnh đường rộng lớn. Ánh nến lập lòe soi bóng những cây cột "
    "đá xám. Một luồng gió lạnh thổi qua khe cửa hẹp.\n\n"
    "Người gác cổng cúi đầu chào. Hắn gật đầu đáp lễ rồi sải bước đi tiếp."
)


# --------------------------------------------------------------------------- #
# Unit tests
# --------------------------------------------------------------------------- #


def test_style_audit_due() -> None:
    assert style_audit_due(10)
    assert style_audit_due(20)
    assert not style_audit_due(3)
    assert not style_audit_due(11)


def test_style_metrics_shape() -> None:
    metrics = style_metrics(_BASE)
    assert metrics["sentence_count"] > 0
    assert metrics["avg_sentence_words"] > 0
    assert 0.0 <= metrics["lexical_diversity"] <= 1.0
    assert isinstance(metrics["top_terms"], list)


def test_report_ok_when_similar() -> None:
    novel = _tmp()
    # Single-chapter baseline identical to the current chapter → no drift.
    _write_chapter(novel, 1, _BASE)
    _write_chapter(novel, 10, _BASE)
    report = build_style_coherence_report(novel, 10, baseline_chapters=(1,))
    assert report["status"] == "ok"
    assert report["drift"] == {}


def test_report_warning_on_drift() -> None:
    novel = _tmp()
    for ch in (1, 2, 3):
        _write_chapter(novel, ch, _BASE)
    # Wildly different style: one long run-on, no dialogue, low diversity.
    drifted = "đi " * 400
    _write_chapter(novel, 10, drifted)
    report = build_style_coherence_report(novel, 10)
    assert report["status"] == "warning"
    assert report["drift"]


def test_report_skipped_when_missing() -> None:
    novel = _tmp()
    report = build_style_coherence_report(novel, 10)
    assert report["status"] == "skipped"


def test_audit_writes_reports() -> None:
    novel = _tmp()
    for ch in (1, 2, 3):
        _write_chapter(novel, ch, _BASE)
    _write_chapter(novel, 10, _BASE)
    result = audit(str(novel), 10)
    json_path = novel / "reviews" / "style_coherence" / "chapter_010_style_audit.json"
    md_path = novel / "reviews" / "style_coherence" / "chapter_010_style_audit.md"
    assert json_path.exists() and md_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["chapter"] == 10
    assert "written" in result


def test_self_registration() -> None:
    entry = registry.get("novelkit_style_coherence")
    assert entry.fn is style_coherence_tool


# --------------------------------------------------------------------------- #
# Property-based tests
# --------------------------------------------------------------------------- #


@settings(max_examples=150)
@given(st.text())
def test_style_metrics_never_raises_and_bounded(text: str) -> None:
    metrics = style_metrics(text)
    assert metrics["sentence_count"] >= 0
    assert 0.0 <= metrics["lexical_diversity"] <= 1.0
    assert 0.0 <= metrics["dialogue_ratio"] <= 1.0


@settings(max_examples=50)
@given(st.integers(min_value=-5, max_value=500))
def test_audit_due_only_on_cadence(chapter: int) -> None:
    due = style_audit_due(chapter)
    if due:
        assert chapter > 3 and chapter % 10 == 0


# --------------------------------------------------------------------------- #
# Staleness / repetition (anti-"mòn văn phong")
# --------------------------------------------------------------------------- #


def test_repetition_flags_repeated_opening_line() -> None:
    from tools.novelkit_style_coherence_tool import build_repetition_report

    novel = _tmp() / "rep"
    same_open = "Hắn mở mắt ra nhìn trần nhà mục nát phía trên đầu mình."
    # Chapters 1-4 all open with the exact same sentence → chapter 4 is stale.
    for ch in range(1, 5):
        _write_chapter(
            novel, ch,
            f"{same_open} Sau đó chương {ch} diễn ra theo một hướng khác nhau hoàn toàn.",
        )

    report = build_repetition_report(novel, 4)
    assert report["status"] == "warning"
    flags = report["flags"]
    assert "repeated_opening_line" in flags
    # Stale opening n-gram recurs across the whole window too.
    assert "stale_opening_pattern" in flags


def test_repetition_clean_when_openings_differ() -> None:
    from tools.novelkit_style_coherence_tool import build_repetition_report

    novel = _tmp() / "fresh"
    openings = [
        "Mưa đổ xối xả trên nóc điện Tàng Kinh suốt cả đêm dài.",
        "Tiếng chuông đồng vang lên ba hồi giữa khu chợ đông đúc.",
        "Lão già bán thuốc nhếch mép cười khi thấy hắn bước tới.",
        "Trên đỉnh núi tuyết, một bóng người áo trắng đứng bất động.",
    ]
    for ch, op in enumerate(openings, start=1):
        _write_chapter(novel, ch, f"{op} Phần còn lại của chương trôi qua êm đềm.")

    report = build_repetition_report(novel, 4)
    assert report["status"] == "ok"
    assert report["flags"] == {}


def test_audit_includes_repetition_block() -> None:
    novel = _tmp() / "aud"
    same_open = "Hắn mở mắt ra nhìn trần nhà mục nát phía trên đầu."
    for ch in range(1, 5):
        _write_chapter(novel, ch, f"{same_open} Nội dung chương {ch} khác biệt rõ ràng.")

    report = audit(str(novel), 4, baseline_chapters=(1, 2, 3), write=False)
    assert "repetition" in report
    assert report["repetition"]["status"] == "warning"
