"""Tests for the strand tool (Task 9.2, Requirements 11/17/18).

Covers strand detection (incl. explicit frontmatter override), the rolling
pacing report, append-only open-loop tracking, payoff detection, the ``weave``
interface, plot-thread migration idempotency, and self-registration.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tools import registry
from tools.novelkit_strand_tool import (
    STRAND_VALUES,
    ChapterStrand,
    OpenLoopEvent,
    detect_loop_payoff,
    detect_strand,
    extract_loops_from_outline,
    get_active_loops,
    migrate_plot_threads,
    pacing_report,
    parse_frontmatter,
    record_chapter_strand,
    record_loop_event,
    strand_tool,
    weave,
)


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


# --------------------------------------------------------------------------- #
# Strand detection
# --------------------------------------------------------------------------- #


def test_detect_strand_quest() -> None:
    result = detect_strand("Hắn chiến đấu, tấn công kẻ thù, huyết chiến.", 1)
    assert result.dominant_strand == "quest"
    assert not result.explicit


def test_detect_strand_explicit_override_wins() -> None:
    # Prose is quest-flavored, but frontmatter forces fire.
    result = detect_strand("Hắn chiến đấu tấn công.", 1, {"strand": "fire"})
    assert result.dominant_strand == "fire"
    assert result.explicit
    assert result.weight == 1.0


def test_detect_strand_invalid_override_ignored() -> None:
    result = detect_strand("Hắn yêu nàng, nhớ nhung.", 1, {"strand": "bogus"})
    assert result.dominant_strand in STRAND_VALUES
    assert not result.explicit


def test_parse_frontmatter() -> None:
    fm, body = parse_frontmatter("---\nstrand: fire\n---\nNội dung chương.")
    assert fm["strand"] == "fire"
    assert body.strip() == "Nội dung chương."


def test_pacing_report_quest_overload() -> None:
    novel = _tmp()
    for ch in range(1, 8):
        record_chapter_strand(
            novel, ChapterStrand(chapter=ch, dominant_strand="quest", weight=1.0)
        )
    report = pacing_report(novel, 7)
    assert report.quest_streak == 7
    assert "PACING_QUEST_OVERLOAD" in report.issues


# --------------------------------------------------------------------------- #
# Open loops
# --------------------------------------------------------------------------- #


def test_open_loop_lifecycle_append_only() -> None:
    novel = _tmp()
    evs = extract_loops_from_outline("Hắn thề trả thù. Một bí mật về thân thế.", 1)
    assert evs
    for e in evs:
        record_loop_event(novel, e)
    active = get_active_loops(novel)
    assert len(active) == len(evs)

    # Close one loop by appending a closure event (never rewrites the log).
    closures = detect_loop_payoff(active[0].content, [active[0]])
    for c in closures:
        record_loop_event(novel, c)
    assert len(get_active_loops(novel)) == len(evs) - len(closures)


def test_weave_surfaces_open_loops_and_due_payoffs() -> None:
    novel = _tmp()
    e = OpenLoopEvent(
        event_id="loop-ch0001-001",
        event_type="open_loop_created",
        subject="three_year_promise",
        chapter_planted=1,
        content="Lời thề ba năm",
        loop_type="vow",
        urgency="high",
        loop_deadline=3,
    )
    record_loop_event(novel, e)
    result = weave(novel, 5)  # chapter 5 > deadline 3 → overdue
    assert len(result["open_loops"]) == 1
    assert len(result["due_payoffs"]) == 1
    # No expected_payoff set → orphan seed.
    assert len(result["orphan_seeds"]) == 1


def test_migrate_plot_threads_idempotent() -> None:
    novel = _tmp()
    threads = novel / "database" / "plot_threads"
    threads.mkdir(parents=True)
    (threads / "main.md").write_text(
        "## Lời nguyền cổ\nMột lời nguyền từ chương 5 đe dọa nhân vật.\n",
        encoding="utf-8",
    )
    first = migrate_plot_threads(novel)
    assert len(first) == 1
    # Second run is a no-op (stable migrated- ids).
    assert migrate_plot_threads(novel) == []


def test_self_registration() -> None:
    entry = registry.get("novelkit_strand")
    assert entry.fn is strand_tool


def test_tool_dispatch_weave() -> None:
    novel = _tmp()
    out = strand_tool("weave", novel_path=str(novel), chapter=1)
    assert out["open_loops"] == []


# --------------------------------------------------------------------------- #
# Property-based tests
# --------------------------------------------------------------------------- #


@settings(max_examples=200)
@given(st.text(), st.integers(min_value=1, max_value=999))
def test_detect_strand_always_valid(text: str, chapter: int) -> None:
    result = detect_strand(text, chapter)
    assert result.dominant_strand in STRAND_VALUES
    assert 0.5 <= result.weight <= 1.0


@settings(max_examples=100)
@given(
    st.lists(
        st.sampled_from(["thề", "bí mật", "kẻ thù", "huyết mạch", "nợ", "lời nguyền"]),
        max_size=8,
    )
)
def test_extract_then_active_count_matches(markers: list[str]) -> None:
    novel = _tmp()
    outline = " ".join(markers)
    events = extract_loops_from_outline(outline, 1)
    for e in events:
        record_loop_event(novel, e)
    # Every created loop with no closure is active.
    assert len(get_active_loops(novel)) == len(events)
