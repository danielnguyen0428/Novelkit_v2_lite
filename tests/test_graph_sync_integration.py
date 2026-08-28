"""Task 5 — sync integration for the knowledge graph (Req 7; P11 non-regression).

Best-effort KG rebuild runs at sync time only behind the ``graph`` flag, never
breaks sync, and registers the ``graph_updated`` checkpoint step.
"""

from pathlib import Path

from tools.novelkit_sync_tool import _maybe_build_graph  # helper added in Step 3


def test_graph_skipped_when_flag_off(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "longform.json").write_text('{"flags":{"graph":false}}', "utf-8")
    _maybe_build_graph(tmp_path, 1)
    assert not (tmp_path / "logs" / "knowledge_graph.json").exists()


def test_graph_built_when_flag_on(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "database" / "characters").mkdir(parents=True)
    (tmp_path / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")
    (tmp_path / "config" / "longform.json").write_text('{"flags":{"graph":true}}', "utf-8")
    _maybe_build_graph(tmp_path, 1)
    assert (tmp_path / "logs" / "knowledge_graph.json").exists()


def test_checkpoint_step_registered():
    from tools.novelkit_pipeline_state_store import CHECKPOINT_STEPS

    assert "graph_updated" in CHECKPOINT_STEPS
