"""In-progress novel → compass-mode migration (Req 11.4; P14)."""

from __future__ import annotations

import bootstrap  # noqa: F401
from delegate import delegate_tool
from tools.novelkit_compass_tool import COMPASS_REL, read_arc_map


def test_migrate_to_compass_marks_written_arc_done(tmp_path):
    out = delegate_tool(
        "novelkit_compass", action="migrate_to_compass", novel_path=str(tmp_path),
        current_chapter=12, target_chapters=300,
    )
    assert out["expanded_through_chapter"] == 12
    assert (tmp_path / COMPASS_REL).exists()
    arcs = read_arc_map(tmp_path).arcs
    assert arcs and arcs[0].status == "done" and arcs[0].end_chapter == 12


def test_migrate_to_compass_idempotent(tmp_path):
    kw = dict(action="migrate_to_compass", novel_path=str(tmp_path),
              current_chapter=12, target_chapters=300)
    first = delegate_tool("novelkit_compass", **kw)
    second = delegate_tool("novelkit_compass", **kw)
    assert first["changed"] is True
    assert second["changed"] is False  # idempotent (P14)


def test_migrate_short_novel_respects_min_arc_len(tmp_path):
    delegate_tool("novelkit_compass", action="migrate_to_compass",
                  novel_path=str(tmp_path), current_chapter=3, target_chapters=50)
    arc = read_arc_map(tmp_path).arcs[0]
    assert arc.estimated_chapters >= 8  # MIN_ARC_LEN
    read_arc_map(tmp_path).validate()  # still a valid arc map
