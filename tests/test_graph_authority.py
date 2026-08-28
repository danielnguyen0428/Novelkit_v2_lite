"""Regression: the knowledge-graph persist file is DERIVATIVE, never CANON.

``logs/knowledge_graph.json`` is a rebuildable, derived artifact (Req 3.4).
The context-engine already classifies anything under ``logs/`` as the lowest
authority tier via ``_DERIVATIVE_PREFIXES``; this test locks that behaviour in
so the graph file can never be silently promoted above canon (Property P25).
"""

from __future__ import annotations

from plugins.context_engine.novelkit_context import (
    AuthorityTier,
    authority_rank_for_path,
)


def test_kg_is_derivative() -> None:
    assert (
        authority_rank_for_path("logs/knowledge_graph.json")
        == AuthorityTier.DERIVATIVE
    )
