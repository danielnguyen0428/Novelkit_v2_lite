# tests/test_graph_contradictions.py
"""Task 4 — tiered contradiction detection + rewrite-queue enqueue (Req 4; P27).

``detect_contradictions`` is pure/read-only (P27/P28): it loads the persisted
KG and returns tiered findings without mutating anything. ``apply_contradictions``
is the separate write step that enqueues idempotent ``rewrite_queue`` entries on
a ``PipelineState`` payload.
"""
from pathlib import Path

from tools.novelkit_graph_tool import (
    apply_contradictions,
    build,
    detect_contradictions,
)


def _novel_dead_then_acts(tmp_path: Path) -> Path:
    (tmp_path / "database" / "characters").mkdir(parents=True)
    (tmp_path / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")
    from plugins.memory.novelkit_memory import get_provider

    p = get_provider()
    p.add(
        {"category": "timeline", "subject": "A", "field": "death",
         "value": "A chết", "source_chapter": 50, "payload": {}},
        scope=tmp_path,
    )
    p.add(
        {"category": "character_state", "subject": "A", "field": "state_change",
         "value": "A vung kiếm", "source_chapter": 80, "payload": {}},
        scope=tmp_path,
    )
    build(str(tmp_path))
    return tmp_path


def test_hard_contradiction_detected(tmp_path):
    novel = _novel_dead_then_acts(tmp_path)
    r = detect_contradictions(str(novel))
    codes = {c["code"] for c in r["hard"]}
    assert "kg_dead_but_acts" in codes
    assert 80 in r["hard"][0]["affected_chapters"]


def test_apply_enqueues_idempotent(tmp_path):
    novel = _novel_dead_then_acts(tmp_path)
    hard = detect_contradictions(str(novel))["hard"]
    state = {"schema_version": 3, "novel": "x", "tasks": [], "breaker": {},
             "creative": {"mode": "compass"}, "target_chapters": 300,
             "arc_size": 50, "window_size": 5, "min_remaining": 3}
    r1 = apply_contradictions(str(novel), state, hard)
    r2 = apply_contradictions(str(novel), r1["state"], hard)
    q1 = r1["state"]["creative"]["rewrite_queue"]
    q2 = r2["state"]["creative"]["rewrite_queue"]
    assert len(q1) >= 1 and len(q2) == len(q1)  # idempotent


def test_recovery_in_summary_clears_terminal(tmp_path):
    """A revive described only in the event summary (not the event_type) must
    clear the terminal state so a later action is NOT a false kg_dead_but_acts
    (G2: recovery is scanned across event_type AND summary)."""
    (tmp_path / "database" / "characters").mkdir(parents=True)
    (tmp_path / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")
    from plugins.memory.novelkit_memory import get_provider

    p = get_provider()
    p.add({"category": "timeline", "subject": "A", "field": "death",
           "value": "A chết", "source_chapter": 50, "payload": {}}, scope=tmp_path)
    # Recovery expressed in the value/summary, generic field.
    p.add({"category": "timeline", "subject": "A", "field": "event",
           "value": "A revive nhờ đan dược", "source_chapter": 60,
           "payload": {}}, scope=tmp_path)
    p.add({"category": "character_state", "subject": "A", "field": "state_change",
           "value": "A vung kiếm", "source_chapter": 80, "payload": {}},
          scope=tmp_path)
    build(str(tmp_path))
    codes = {c["code"] for c in detect_contradictions(str(tmp_path))["hard"]}
    assert "kg_dead_but_acts" not in codes  # recovery cleared the terminal state


def test_timeline_location_subject_not_phantom_character(tmp_path):
    """A timeline subject that is a place/faction must NOT be classified as a
    character entity (G4: phantom-character prevention)."""
    (tmp_path / "database" / "characters").mkdir(parents=True)
    from plugins.memory.novelkit_memory import get_provider
    from tools.novelkit_graph_model import _entity_id, build_graph
    from tools.novelkit_graph_tool import _collect_sources

    p = get_provider()
    p.add({"category": "timeline", "subject": "Hợp Hoan Tông", "field": "event",
           "value": "tông môn bị vây", "source_chapter": 10, "payload": {}},
          scope=tmp_path)
    g = build_graph(_collect_sources(tmp_path))
    node = g.nodes[_entity_id("Hợp Hoan Tông")]
    assert node["entity_kind"] != "character"
