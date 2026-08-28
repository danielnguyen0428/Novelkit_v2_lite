"""Flexible arc-map boundaries + legacy fallback (Req 4; Property P16)."""

from __future__ import annotations

import pytest

from tools.novelkit_arcmap import ArcMap, ArcMapError, ArcSpec, MIN_ARC_LEN
from tools.novelkit_pipeline_tool import compute_arc, is_arc_boundary


def _two_arc_map() -> ArcMap:
    return ArcMap.from_dict(
        {
            "arcs": [
                {
                    "arc_id": "a1", "start_chapter": 1, "end_chapter": 12,
                    "estimated_chapters": 12, "arc_type": "growth_breakthrough",
                    "status": "done",
                },
                {
                    "arc_id": "a2", "start_chapter": 13, "end_chapter": 30,
                    "estimated_chapters": 18, "arc_type": "tournament",
                    "status": "detailed",
                },
            ]
        }
    )


def test_arcmap_partitions_and_lookup():
    am = _two_arc_map()
    am.validate()
    assert am.arc_index_for(20) == 2
    assert am.arc_index_for(1) == 1
    assert am.is_last_chapter_of_arc(12) is True
    assert am.is_last_chapter_of_arc(11) is False


def test_arcmap_rejects_gap():
    am = ArcMap.from_dict(
        {"arcs": [
            {"arc_id": "a1", "start_chapter": 1, "end_chapter": 12,
             "estimated_chapters": 12, "arc_type": "tournament"},
            {"arc_id": "a2", "start_chapter": 20, "end_chapter": 40,  # gap!
             "estimated_chapters": 21, "arc_type": "secret_realm"},
        ]}
    )
    with pytest.raises(ArcMapError):
        am.validate()


def test_arcmap_rejects_too_short():
    am = ArcMap.from_dict(
        {"arcs": [{"arc_id": "a1", "start_chapter": 1, "end_chapter": 4,
                   "estimated_chapters": 4, "arc_type": "tournament"}]}
    )
    with pytest.raises(ArcMapError):
        am.validate()
    assert MIN_ARC_LEN == 8


def test_skeleton_arc_not_required_to_be_placed():
    am = ArcMap.from_dict(
        {"arcs": [
            {"arc_id": "a1", "start_chapter": 1, "end_chapter": 12,
             "estimated_chapters": 12, "arc_type": "growth_breakthrough"},
            {"arc_id": "a2", "start_chapter": None, "end_chapter": None,
             "estimated_chapters": 20, "arc_type": "secret_realm", "status": "skeleton"},
        ]}
    )
    am.validate()  # skeleton arc excluded from coverage check


def test_compute_arc_fallback_matches_legacy():
    # No arc map → must equal the exact legacy arithmetic.
    assert compute_arc(73, arc_map=None, arc_size=50) == 2
    assert compute_arc(1, arc_size=50) == 1
    assert compute_arc(50, arc_size=50) == 1
    assert compute_arc(51, arc_size=50) == 2


def test_compute_arc_uses_arc_map_when_present():
    am = _two_arc_map()
    assert compute_arc(20, arc_map=am, arc_size=50) == 2  # arc_map wins
    # chapter beyond placed arcs falls back to arithmetic, no crash
    assert compute_arc(200, arc_map=am, arc_size=50) == 4


def test_is_arc_boundary_fact_and_map_and_fallback():
    am = _two_arc_map()
    assert is_arc_boundary(12, arc_map=am) is True          # arc end via map
    assert is_arc_boundary(11, arc_map=am) is False
    assert is_arc_boundary(7, arc_end_fact=True) is True     # fact always wins
    assert is_arc_boundary(50, arc_size=50) is True          # legacy fallback
    assert is_arc_boundary(49, arc_size=50) is False


def test_arcmap_digest_idempotent_and_upsert():
    am = _two_arc_map()
    d1 = am.digest()
    assert am.upsert(ArcSpec.from_dict(am.arcs[0].to_dict())) is False  # no change
    assert am.digest() == d1
    assert am.upsert(ArcSpec(arc_id="a3", arc_type="secret_realm",
                             estimated_chapters=20, status="skeleton")) is True
    assert am.digest() != d1
