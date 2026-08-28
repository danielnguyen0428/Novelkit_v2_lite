# tests/test_graph_query.py
from pathlib import Path
from delegate import delegate_tool
from tools.novelkit_graph_tool import build


def _novel_with_rel(tmp_path: Path):
    (tmp_path / "database" / "characters").mkdir(parents=True)
    for n in ("A", "B"):
        (tmp_path / "database" / "characters" / f"{n}.md").write_text(f"# {n}\n", "utf-8")
    return tmp_path


def test_neighbors_pure_and_bounded(tmp_path):
    novel = _novel_with_rel(tmp_path); build(str(novel))
    r1 = delegate_tool("novelkit_graph", action="query", novel_path=str(novel),
                       kind="neighbors", node="ent:a", hops=1)
    r2 = delegate_tool("novelkit_graph", action="query", novel_path=str(novel),
                       kind="neighbors", node="ent:a", hops=1)
    assert r1 == r2                              # deterministic (P28)


def test_query_missing_node_empty(tmp_path):
    novel = _novel_with_rel(tmp_path); build(str(novel))
    r = delegate_tool("novelkit_graph", action="query", novel_path=str(novel),
                      kind="timeline_of", node="ent:nobody")
    assert r["events"] == []
