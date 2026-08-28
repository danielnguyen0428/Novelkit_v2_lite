"""Story Compass / layered outline / arc map tool (Req 1, 2, 4; Property P14)."""

from __future__ import annotations

import bootstrap  # noqa: F401 — brings the tool surface online
from delegate import delegate_tool
from tools.novelkit_compass_tool import (
    ARC_MAP_REL,
    COMPASS_REL,
    read_compass,
)


def test_update_compass_idempotent(tmp_path):
    kwargs = dict(
        ending_direction="MC đạt Đại Thừa, trả xong nợ nhân quả",
        active_long_threads=[{"id": "T-001", "name": "thân thế", "status": "open"}],
        scale_estimate={"volumes": 8, "arcs": 40, "chapters": 600},
        current_volume_id="vol_001",
        current_arc_id="arc_001",
    )
    a = delegate_tool("novelkit_compass", action="update_compass",
                      novel_path=str(tmp_path), **kwargs)
    b = delegate_tool("novelkit_compass", action="update_compass",
                      novel_path=str(tmp_path), **kwargs)
    assert a["changed"] is True
    assert b["changed"] is False  # idempotent (P14)
    assert a["compass_digest"] == b["compass_digest"]
    assert (tmp_path / COMPASS_REL).exists()


def test_compass_roundtrip(tmp_path):
    delegate_tool(
        "novelkit_compass", action="update_compass", novel_path=str(tmp_path),
        ending_direction="X", active_long_threads=[], scale_estimate={"chapters": 600},
        current_volume_id="vol_001", current_arc_id="arc_003",
    )
    data = read_compass(tmp_path)
    assert data["ending_direction"] == "X"
    assert data["current_arc_id"] == "arc_003"
    assert data["scale_estimate"]["chapters"] == 600


def test_upsert_arc_idempotent_and_plan_expansion(tmp_path):
    arc1 = {"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
            "estimated_chapters": 12, "arc_type": "growth_breakthrough",
            "status": "done", "volume_id": "vol_001"}
    arc2 = {"arc_id": "arc_002", "start_chapter": None, "end_chapter": None,
            "estimated_chapters": 18, "arc_type": "tournament",
            "status": "skeleton", "volume_id": "vol_001"}
    r1 = delegate_tool("novelkit_compass", action="upsert_arc",
                       novel_path=str(tmp_path), arc=arc1)
    delegate_tool("novelkit_compass", action="upsert_arc",
                  novel_path=str(tmp_path), arc=arc2)
    r1b = delegate_tool("novelkit_compass", action="upsert_arc",
                        novel_path=str(tmp_path), arc=arc1)
    assert r1["changed"] is True and r1b["changed"] is False  # P14
    assert (tmp_path / ARC_MAP_REL).exists()

    plan = delegate_tool("novelkit_compass", action="plan_expansion",
                         novel_path=str(tmp_path))
    assert plan["kind"] == "arc" and plan["target_id"] == "arc_002"
    assert plan["expand_task_key"] == "arc.arc_002.expand"


def test_boundary_check(tmp_path):
    for arc in (
        {"arc_id": "arc_001", "start_chapter": 1, "end_chapter": 12,
         "estimated_chapters": 12, "arc_type": "growth_breakthrough",
         "status": "done", "volume_id": "vol_001"},
        {"arc_id": "arc_002", "start_chapter": 13, "end_chapter": 30,
         "estimated_chapters": 18, "arc_type": "tournament",
         "status": "detailed", "volume_id": "vol_001"},
    ):
        delegate_tool("novelkit_compass", action="upsert_arc",
                      novel_path=str(tmp_path), arc=arc)
    assert delegate_tool("novelkit_compass", action="boundary_check",
                         novel_path=str(tmp_path), chapter=12)["at_arc_end"] is True
    end = delegate_tool("novelkit_compass", action="boundary_check",
                        novel_path=str(tmp_path), chapter=30)
    assert end["at_arc_end"] is True and end["at_volume_end"] is True
