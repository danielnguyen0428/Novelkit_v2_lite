"""Layered summaries: canon authority + reindex + coverage (Req 3; P15, P5)."""

from __future__ import annotations

import bootstrap  # noqa: F401 — brings the tool surface online
from delegate import delegate_tool
from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    authority_rank_for_path,
)
from tools.novelkit_sync_tool import _iter_canon_files, health_check


def test_summaries_rank_as_canon():
    assert authority_rank_for_path("summaries/arc_arc_001.md") == AuthorityTier.CANON
    assert authority_rank_for_path("summaries/volume_vol_001.md") == AuthorityTier.CANON


def test_summaries_are_reindexed(tmp_path):
    (tmp_path / "summaries").mkdir()
    (tmp_path / "summaries" / "arc_arc_001.md").write_text(
        "# Arc 1 summary\nMC đột phá Trúc Cơ.", encoding="utf-8"
    )
    files = {p.relative_to(tmp_path).as_posix() for p in _iter_canon_files(tmp_path)}
    assert "summaries/arc_arc_001.md" in files


def _seed_arc(novel_path, status, with_summary):
    delegate_tool(
        "novelkit_compass", action="upsert_arc", novel_path=str(novel_path),
        arc={"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
             "estimated_chapters": 12, "arc_type": "growth_breakthrough",
             "status": status, "volume_id": "vol_001"},
    )
    if with_summary:
        (novel_path / "summaries").mkdir(exist_ok=True)
        (novel_path / "summaries" / "arc_arc_001.md").write_text("done", encoding="utf-8")
        # arc_001 is the only (and last) arc of vol_001, so a finished volume
        # also expects a volume summary.
        (novel_path / "summaries" / "volume_vol_001.md").write_text("done", encoding="utf-8")


def test_doctor_flags_missing_arc_summary(tmp_path):
    _seed_arc(tmp_path, status="done", with_summary=False)
    codes = {i.code for i in health_check(tmp_path)}
    assert "summary_missing" in codes


def test_doctor_no_flag_when_summary_present(tmp_path):
    _seed_arc(tmp_path, status="done", with_summary=True)
    issues = [i for i in health_check(tmp_path) if i.code == "summary_missing"]
    assert issues == []


def test_doctor_no_flag_for_unfinished_arc(tmp_path):
    _seed_arc(tmp_path, status="detailed", with_summary=False)
    issues = [i for i in health_check(tmp_path) if i.code == "summary_missing"]
    assert issues == []
