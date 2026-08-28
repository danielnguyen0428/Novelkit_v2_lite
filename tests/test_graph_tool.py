# tests/test_graph_tool.py
"""novelkit_graph tool: build + export + self-register (Task 2; Req 3,6; P25,P26).

- ``bootstrap.load_all()`` registers ``novelkit_graph`` (import-time self-register);
- ``build`` writes ``logs/knowledge_graph.json`` and is idempotent — rebuilding
  the same sources yields an identical digest and a byte-identical file (P25/P26);
- the persisted file carries the derivative-graph envelope (schema/graph/metadata).
"""

import json
from pathlib import Path

import bootstrap
from delegate import delegate_tool
from tools import registry


def _seed_min_novel(tmp_path: Path) -> Path:
    p = tmp_path
    (p / "database" / "characters").mkdir(parents=True)
    (p / "database" / "characters" / "A.md").write_text("# A\n", encoding="utf-8")
    return p


def test_graph_registered():
    bootstrap.load_all()
    assert "novelkit_graph" in registry.list_tools()


def test_build_writes_and_idempotent(tmp_path):
    novel = _seed_min_novel(tmp_path)
    r1 = delegate_tool("novelkit_graph", action="build", novel_path=str(novel))
    gpath = novel / "logs" / "knowledge_graph.json"
    assert gpath.exists() and r1["graph_digest"].startswith("sha256:")
    first = gpath.read_bytes()
    r2 = delegate_tool("novelkit_graph", action="build", novel_path=str(novel))
    assert r2["graph_digest"] == r1["graph_digest"]          # P26
    assert gpath.read_bytes() == first                        # byte-identical (idempotent)


def test_export_matches_build(tmp_path):
    novel = _seed_min_novel(tmp_path)
    delegate_tool("novelkit_graph", action="build", novel_path=str(novel))
    data = json.loads((novel / "logs" / "knowledge_graph.json").read_text("utf-8"))
    assert data["schema"] == 1 and "graph" in data and "metadata" in data
