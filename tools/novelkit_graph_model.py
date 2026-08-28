"""Pure knowledge-graph model: build a networkx MultiDiGraph from structured
sources, plus a stable digest + node-link (de)serialisation (Req 1, 2, 3; P26).

No LLM, no I/O — deterministic over its inputs so it is verifiable in isolation.
Depends only on stdlib + networkx (the one third-party dependency added by this
feature). Must NOT import novelkit_graph_tool (avoid an import cycle).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

import networkx as nx


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str  # entity | relationship | event
    props: dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass(frozen=True)
class GraphEdge:
    src: str
    dst: str
    label: str  # participates_in | affects | subject | object | member_of | located_in | belongs_to
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSources:
    """Read-only, already-structured inputs (no LLM). Each item is a plain dict
    mirroring a MemoryItem row or a canon fact."""
    relationships: list[dict[str, Any]] = field(default_factory=list)
    character_states: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    minor_cast: list[dict[str, Any]] = field(default_factory=list)
    open_loops: list[dict[str, Any]] = field(default_factory=list)
    world_rules: list[dict[str, Any]] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)          # names from database/characters/
    arc_edges: list[dict[str, Any]] = field(default_factory=list)  # {chapter, arc_id, volume_id}


def _slug(text: str) -> str:
    keep = "".join(c if c.isalnum() else "_" for c in text.strip().lower())
    return "_".join(p for p in keep.split("_") if p) or "x"


def _entity_id(name: str) -> str:
    return f"ent:{_slug(name)}"


def _event_id(chapter: Any, kind: str, subject: str) -> str:
    return f"evt:ch{int(chapter):04d}:{kind}:{_slug(subject)}"


def _rel_id(subject: str) -> str:
    return f"rel:{_slug(subject)}"


def build_graph(sources: GraphSources) -> nx.MultiDiGraph:
    """Deterministically assemble the KG. Pure over ``sources`` (P26)."""
    g = nx.MultiDiGraph()

    def ensure_entity(name: str, entity_kind: str, *, source: str = "",
                      chapter: Optional[int] = None) -> str:
        nid = _entity_id(name)
        if nid not in g:
            g.add_node(nid, kind="entity", entity_kind=entity_kind, name=name,
                       aliases=[], first_seen=chapter, last_seen=chapter, source=source)
        else:
            data = g.nodes[nid]
            if chapter is not None:
                fs, ls = data.get("first_seen"), data.get("last_seen")
                data["first_seen"] = chapter if fs is None else min(fs, chapter)
                data["last_seen"] = chapter if ls is None else max(ls, chapter)
        return nid

    # Main-cast characters (canon files) first so minor_cast never duplicates them.
    for name in sorted(sources.characters):
        ensure_entity(name, "character", source="database/characters/")

    for mc in sorted(sources.minor_cast, key=lambda r: str(r.get("subject"))):
        name = str(mc.get("subject"))
        if _entity_id(name) in g and g.nodes[_entity_id(name)]["entity_kind"] == "character":
            continue  # Req 1.6: do not duplicate a main-cast character as minor_cast
        payload = mc.get("payload") or {}
        nid = ensure_entity(name, "minor_cast", source=f"minor_cast:{name}",
                            chapter=payload.get("first_seen") or mc.get("source_chapter"))
        g.nodes[nid]["last_seen"] = payload.get("last_seen") or g.nodes[nid].get("last_seen")

    for wr in sorted(sources.world_rules, key=lambda r: str(r.get("subject"))):
        ensure_entity(str(wr.get("subject")), "world_rule", source="world_rules")

    # Reified relationships.
    for rel in sorted(sources.relationships, key=lambda r: str(r.get("subject"))):
        subj = str(rel.get("subject"))          # canonical "A↔B"
        payload = rel.get("payload") or {}
        a, b = payload.get("a"), payload.get("b")
        if not (a and b) and "↔" in subj:
            a, b = subj.split("↔", 1)
        rid = _rel_id(subj)
        g.add_node(rid, kind="relationship", rel_type=str(rel.get("value")),
                   status=str(payload.get("status") or "active"),
                   start_chapter=rel.get("source_chapter"),
                   end_chapter=payload.get("end_chapter"), source=f"relationships:{subj}")
        if a and b:
            ea, eb = ensure_entity(str(a).strip(), "character"), ensure_entity(str(b).strip(), "character")
            g.add_edge(rid, ea, key="subject", label="subject")
            g.add_edge(rid, eb, key="object", label="object")

    # Events from character_state + timeline.
    #
    # ``entity_kind`` is only applied when the entity is *first* created. A
    # character_state subject is genuinely a character, so it seeds "character".
    # A timeline subject is ambiguous (could be a location/faction/event), so it
    # must NOT be asserted as a character — otherwise a place like "Hợp Hoan Tông"
    # becomes a phantom character that contradiction detection checks as if it
    # were a person. It seeds the neutral "concept" kind instead; if the same
    # subject was already seeded as a character (character_state runs first), that
    # stronger classification is preserved by ensure_entity.
    def add_event(subject: str, event_type: str, chapter: Any, value: str,
                  source: str, commit_id: Optional[str],
                  *, entity_kind: str = "character") -> None:
        if chapter is None:
            return
        ent = ensure_entity(subject, entity_kind, chapter=int(chapter))
        eid = _event_id(chapter, event_type, subject)
        g.add_node(eid, kind="event", chapter=int(chapter), event_type=event_type,
                   summary=value, source_commit_id=commit_id, source=source)
        g.add_edge(ent, eid, key="participates_in", label="participates_in")
        g.add_edge(eid, ent, key="affects", label="affects")

    for cs in sorted(sources.character_states,
                     key=lambda r: (int(r.get("source_chapter") or 0), str(r.get("subject")))):
        add_event(str(cs.get("subject")), str(cs.get("field") or "state_change"),
                  cs.get("source_chapter"), str(cs.get("value") or ""),
                  "character_state", (cs.get("payload") or {}).get("source_commit_id"))
    for tl in sorted(sources.timeline,
                     key=lambda r: (int(r.get("source_chapter") or 0), str(r.get("subject")))):
        add_event(str(tl.get("subject")), str(tl.get("field") or "timeline"),
                  tl.get("source_chapter"), str(tl.get("value") or ""), "timeline", None,
                  entity_kind="concept")

    # Arc/volume membership edges (belongs_to).
    for ae in sources.arc_edges:
        ch, arc_id, vol_id = ae.get("chapter"), ae.get("arc_id"), ae.get("volume_id")
        if arc_id:
            an = f"arc:{_slug(str(arc_id))}"
            if an not in g:
                g.add_node(an, kind="arc", arc_id=arc_id, source="arc_map")
            if vol_id:
                vn = f"vol:{_slug(str(vol_id))}"
                if vn not in g:
                    g.add_node(vn, kind="volume", volume_id=vol_id, source="layered_outline")
                g.add_edge(an, vn, key="belongs_to", label="belongs_to")
    return g


def _canonical(g: nx.MultiDiGraph) -> bytes:
    nodes = sorted(
        ([n, {k: v for k, v in sorted(d.items())}] for n, d in g.nodes(data=True)),
        key=lambda x: x[0],
    )
    edges = sorted(
        ([u, v, str(k), d.get("label", "")] for u, v, k, d in g.edges(keys=True, data=True)),
        key=lambda x: (x[0], x[1], x[2], x[3]),
    )
    return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def graph_digest(g: nx.MultiDiGraph) -> str:
    return f"sha256:{hashlib.sha256(_canonical(g)).hexdigest()}"


def to_node_link(g: nx.MultiDiGraph) -> dict[str, Any]:
    return nx.node_link_data(g, edges="links")


def from_node_link(data: dict[str, Any]) -> nx.MultiDiGraph:
    return nx.node_link_graph(data, directed=True, multigraph=True, edges="links")


__all__ = ["GraphNode", "GraphEdge", "GraphSources", "build_graph",
           "graph_digest", "to_node_link", "from_node_link"]
