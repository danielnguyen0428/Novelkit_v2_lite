"""Tests for the knowledge-graph config + graph feature flags (Req 10.1, 10.2)."""

from __future__ import annotations

from tools.novelkit_longform_config import load_config, flag_enabled


def test_graph_flags_default_on(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg["flags"]["graph"] is True
    assert cfg["flags"]["graph_llm_enrich"] is True
    assert flag_enabled("graph", tmp_path) is True


def test_kg_config_defaults_loadable():
    from tools.novelkit_graph_tool import load_kg_config

    kg = load_kg_config()
    assert kg["min_conflict_confidence"] == 0.7
    assert "death" in kg["terminal_event_types"]
    assert kg["max_query_hops"] >= 1
