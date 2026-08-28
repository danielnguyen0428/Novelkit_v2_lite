"""4-dimension related-chapter recall + next preview (Req 5; Property P17)."""

from __future__ import annotations

import bootstrap  # noqa: F401
from delegate import delegate_tool
from plugins.memory.novelkit_memory import get_provider


def _seed(novel_path):
    p = get_provider()
    p.commit_episodic(
        scope=novel_path,
        memory_facts=[
            {"category": "minor_cast", "subject": "Lão Chu", "field": "profile",
             "value": "chủ quán", "payload": {"first_seen": 7, "last_seen": 12,
                                              "appearance_count": 2}},
            {"category": "character_state", "subject": "Mộc Trần", "field": "realm",
             "value": "Trúc Cơ sơ kỳ"},
            {"category": "relationships", "subject": "Mộc Trần↔Sư phụ",
             "field": "trust", "value": "tăng"},
        ],
        chapter=12, commit_id="c12",
    )
    # an outline for the "next" chapter
    arc_dir = novel_path / "outlines" / "arc_2"
    arc_dir.mkdir(parents=True)
    (arc_dir / "chapter_051_outline.md").write_text(
        "# Chapter 51 Outline\n## Mục tiêu chương\nĐột phá Trúc Cơ trung kỳ.\n"
        "## Hook ending\nType: Nguy Cơ\n",
        encoding="utf-8",
    )


def test_recall_pure_and_bounded(tmp_path):
    _seed(tmp_path)
    r1 = delegate_tool("novelkit_recall", action="recommend_chapters",
                       novel_path=str(tmp_path), chapter=50, k_per_dim=2)
    r2 = delegate_tool("novelkit_recall", action="recommend_chapters",
                       novel_path=str(tmp_path), chapter=50, k_per_dim=2)
    assert r1 == r2  # pure (P17)
    dims = {x["dimension"] for x in r1["related_chapters"]}
    assert dims <= {"foreshadow", "appearance", "state_change", "relationship"}
    for d in dims:
        assert sum(1 for x in r1["related_chapters"] if x["dimension"] == d) <= 2


def test_recall_includes_next_chapter_preview(tmp_path):
    _seed(tmp_path)
    r = delegate_tool("novelkit_recall", action="recommend_chapters",
                      novel_path=str(tmp_path), chapter=50)
    preview = r["next_chapter_preview"]
    assert preview is not None and preview["chapter"] == 51
    assert "Trúc Cơ" in preview["goal"]


def test_recall_empty_first_chapter(tmp_path):
    r = delegate_tool("novelkit_recall", action="recommend_chapters",
                      novel_path=str(tmp_path), chapter=1)
    assert r["related_chapters"] == []
    assert r["next_chapter_preview"] is None


def test_recall_only_past_chapters(tmp_path):
    _seed(tmp_path)  # facts at chapter 12
    r = delegate_tool("novelkit_recall", action="recommend_chapters",
                      novel_path=str(tmp_path), chapter=12)
    # chapter 12 is "now"; recall must reference strictly-earlier chapters only
    assert all(x["chapter"] < 12 for x in r["related_chapters"])
