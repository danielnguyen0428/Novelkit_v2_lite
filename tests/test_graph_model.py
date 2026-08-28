# tests/test_graph_model.py
from tools.novelkit_graph_model import (
    GraphNode, GraphEdge, GraphSources, build_graph, graph_digest,
    to_node_link, from_node_link,
)

def _sources():
    return GraphSources(
        relationships=[{"subject": "A↔B", "field": "type", "value": "master_disciple",
                        "source_chapter": 3, "payload": {"a": "A", "b": "B"}}],
        character_states=[{"subject": "A", "field": "status", "value": "injured",
                           "source_chapter": 5, "payload": {}}],
        timeline=[], minor_cast=[{"subject": "Lão Chu", "field": "profile",
                                  "value": "chủ quán", "source_chapter": 7,
                                  "payload": {"first_seen": 7, "last_seen": 7}}],
        open_loops=[], world_rules=[], characters=["A", "B"], arc_edges=[],
    )

def test_build_deterministic_digest():
    g1 = build_graph(_sources()); g2 = build_graph(_sources())
    assert graph_digest(g1) == graph_digest(g2)          # P26
    assert g1.number_of_nodes() >= 4                      # A, B, relationship, minor_cast, events

def test_node_link_round_trip():
    g = build_graph(_sources())
    data = to_node_link(g)
    g2 = from_node_link(data)
    assert graph_digest(g) == graph_digest(g2)

def test_empty_sources_valid():
    g = build_graph(GraphSources())
    assert g.number_of_nodes() == 0 and graph_digest(g).startswith("sha256:")
