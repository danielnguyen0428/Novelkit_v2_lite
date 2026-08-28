# tests/test_smoke_graph.py
"""Task 9 — end-to-end smoke over the knowledge graph (Req 10.4, 10.5, 10.6).

Exercises the full spoke in one flow on a tiny synthetic novel: seed memory
(a relationship, a terminal timeline event, a later action) + two canon
characters, then ``build`` → ``query`` (timeline) → ``detect_contradictions``
(hard tier) → ``apply_contradictions`` (rewrite-queue enqueue). Confirms P25–P28
cooperate on a realistic path without regressing P1–P24.
"""
from pathlib import Path

from tools.novelkit_graph_tool import (
    apply_contradictions,
    build,
    detect_contradictions,
    query,
)


def test_smoke_build_query_detect_apply(tmp_path):
    (tmp_path / "database" / "characters").mkdir(parents=True)
    for n in ("A", "B"):
        (tmp_path / "database" / "characters" / f"{n}.md").write_text(f"# {n}\n", "utf-8")

    from plugins.memory.novelkit_memory import get_provider

    p = get_provider()
    p.add(
        {"category": "relationships", "subject": "A↔B", "field": "type",
         "value": "master_disciple", "source_chapter": 3,
         "payload": {"a": "A", "b": "B"}},
        scope=tmp_path,
    )
    p.add(
        {"category": "timeline", "subject": "A", "field": "death",
         "value": "chết", "source_chapter": 50, "payload": {}},
        scope=tmp_path,
    )
    p.add(
        {"category": "character_state", "subject": "A", "field": "state_change",
         "value": "vung kiếm", "source_chapter": 80, "payload": {}},
        scope=tmp_path,
    )

    r = build(str(tmp_path))
    assert r["node_count"] >= 3

    tl = query(str(tmp_path), kind="timeline_of", node="ent:a")
    assert len(tl["events"]) >= 2

    hard = detect_contradictions(str(tmp_path))["hard"]
    assert hard

    state = {"schema_version": 3, "novel": "x", "tasks": [], "breaker": {},
             "creative": {"mode": "compass"}, "target_chapters": 300,
             "arc_size": 50, "window_size": 5, "min_remaining": 3}
    out = apply_contradictions(str(tmp_path), state, hard)
    assert out["enqueued"] >= 1
