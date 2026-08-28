"""CLI `graph` subcommand (Task 7, Req 6.3).

The CLI reaches the ``novelkit_graph`` tool through the same ``delegate_tool``
hub the gateway/cron use. ``graph build`` must persist the derivative graph at
``logs/knowledge_graph.json`` and exit 0.
"""

from pathlib import Path

from cli import main


def test_cli_graph_build(tmp_path, capsys):
    (tmp_path / "database" / "characters").mkdir(parents=True)
    (tmp_path / "database" / "characters" / "A.md").write_text("# A\n", "utf-8")
    rc = main(["graph", "build", "--novel", str(tmp_path)])
    assert rc == 0 and (tmp_path / "logs" / "knowledge_graph.json").exists()
