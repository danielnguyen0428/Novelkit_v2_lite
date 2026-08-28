"""NovelKit knowledge-graph tool (Req 6). Loader tách sớm cho config."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

_LOG = logging.getLogger("novelkit.graph")

_KG_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "knowledge_graph.json"
_KG_DEFAULTS: dict[str, Any] = {
    "entity_kinds": ["character","minor_cast","location","faction","artifact","world_rule","concept"],
    "rel_types": ["master_disciple","kin","ally","enemy","romance","superior_subordinate"],
    "terminal_event_types": ["death","sealed","departed"],
    "recovery_event_types": ["revive","released"],
    "min_conflict_confidence": 0.7,
    "max_query_hops": 4,
    "max_subgraph_nodes": 500,
}

def load_kg_config() -> dict[str, Any]:
    try:
        data = json.loads(_KG_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_KG_DEFAULTS)
    return {**_KG_DEFAULTS, **(data if isinstance(data, dict) else {})}


# --------------------------------------------------------------------------- #
# Build / export (Req 3, 6; P25, P26) — extends the loader above.
#
# The knowledge graph is a *derivative* artifact: it is rebuilt deterministically
# from already-structured sources (episodic memory items + canon character files
# + the arc map) and persisted at ``logs/knowledge_graph.json``. Persisting under
# ``logs/`` means the context-engine already classifies it DERIVATIVE (never a
# canon override, P5). Reads are best-effort so a missing/empty memory store or
# arc map can never crash a build.
# --------------------------------------------------------------------------- #

import os

from tools import registry
from tools.novelkit_graph_model import (
    GraphSources,
    build_graph,
    graph_digest,
    to_node_link,
)

#: Where the persisted derivative graph lives (relative to the novel workspace).
GRAPH_REL_PATH = "logs/knowledge_graph.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` as pretty, key-sorted JSON atomically (temp+fsync+replace).

    ``sort_keys=True`` makes the on-disk bytes a pure function of ``payload``, so a
    rebuild over identical sources is byte-identical (idempotent, P25)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _memory_items(scope: Path, category: str) -> list[dict[str, Any]]:
    """Read active episodic items of ``category`` as plain dicts (best-effort).

    Memory is optional: if the store file is absent, the provider cannot be
    imported, or a query fails, we return ``[]`` so a build never crashes."""
    if not (scope / "memory" / "items.sqlite3").exists():
        return []
    try:
        from plugins.memory.novelkit_memory import get_provider

        items = get_provider().store(scope).query(
            category=category, status="active", limit=100_000
        )
    except Exception:  # noqa: BLE001 — memory optional; build must never crash
        # Best-effort, but never silent: a schema mismatch or store error here
        # would otherwise make the graph build from an empty source and report
        # the story as perfectly consistent. Surface it so a real failure is
        # diagnosable instead of masquerading as "no data".
        _LOG.warning(
            "graph: memory read failed for category %r under %s; treating as empty",
            category, scope, exc_info=True,
        )
        return []
    return [
        {
            "subject": i.subject,
            "field": i.field,
            "value": i.value,
            "source_chapter": i.source_chapter,
            "payload": i.payload,
        }
        for i in items
    ]


def _character_names(scope: Path) -> list[str]:
    """Main-cast names from ``database/characters/*.md`` (``_``-prefixed skipped)."""
    d = scope / "database" / "characters"
    if not d.exists():
        return []
    return sorted(f.stem for f in d.glob("*.md") if not f.stem.startswith("_"))


def _arc_edges(scope: Path) -> list[dict[str, Any]]:
    """Per-chapter arc/volume membership rows from the canon arc map (best-effort)."""
    try:
        from tools.novelkit_compass_tool import read_arc_map

        arcs = read_arc_map(scope).arcs
    except Exception:  # noqa: BLE001 — arc map optional; build must never crash
        _LOG.warning(
            "graph: arc-map read failed under %s; building without arc edges",
            scope, exc_info=True,
        )
        return []
    out: list[dict[str, Any]] = []
    for a in arcs:
        if a.start_chapter and a.end_chapter:
            for ch in range(a.start_chapter, a.end_chapter + 1):
                out.append(
                    {"chapter": ch, "arc_id": a.arc_id, "volume_id": a.volume_id}
                )
    return out


def _collect_sources(scope: Path) -> GraphSources:
    """Gather every structured source the model needs (no LLM, best-effort I/O)."""
    return GraphSources(
        relationships=_memory_items(scope, "relationships"),
        character_states=_memory_items(scope, "character_state"),
        timeline=_memory_items(scope, "timeline"),
        minor_cast=_memory_items(scope, "minor_cast"),
        open_loops=_memory_items(scope, "open_loops"),
        world_rules=_memory_items(scope, "world_rules"),
        characters=_character_names(scope),
        arc_edges=_arc_edges(scope),
    )


def build(novel_path: str | Path, *, through_chapter: int | None = None) -> dict[str, Any]:
    """Rebuild the KG from ``novel_path`` sources and persist it (Req 3.1; P25/P26)."""
    scope = Path(novel_path)
    g = build_graph(_collect_sources(scope))
    digest = graph_digest(g)
    payload = {
        "schema": 1,
        "graph_digest": digest,
        "metadata": {
            "through_chapter": through_chapter,
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
        },
        "graph": to_node_link(g),
    }
    _atomic_write_json(scope / GRAPH_REL_PATH, payload)
    return {
        "graph_digest": digest,
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "path": GRAPH_REL_PATH,
    }


def export(novel_path: str | Path) -> dict[str, Any]:
    """Return a pointer to the persisted graph, building it first if absent."""
    scope = Path(novel_path)
    gp = scope / GRAPH_REL_PATH
    if not gp.exists():
        return build(novel_path)
    data = json.loads(gp.read_text(encoding="utf-8"))
    return {"path": GRAPH_REL_PATH, "graph_digest": data.get("graph_digest")}


def _load_graph(scope: Path):
    """Load the persisted graph, or rebuild it in-RAM when no file exists (P25)."""
    from tools.novelkit_graph_model import from_node_link

    gp = scope / GRAPH_REL_PATH
    if gp.exists():
        return from_node_link(json.loads(gp.read_text(encoding="utf-8"))["graph"])
    return build_graph(_collect_sources(scope))  # in-RAM fallback (P25)


def query(novel_path: str | Path, *, kind: str, **params: Any) -> dict[str, Any]:
    """Read-only, deterministic, bounded multi-hop queries over the KG (Req 5; P28).

    Loads the persisted graph (or rebuilds in-RAM when absent) and never writes.
    All traversals are capped by ``max_query_hops`` / ``max_subgraph_nodes`` from
    the KG config so results stay bounded regardless of graph size (P28)."""
    import networkx as nx

    scope = Path(novel_path)
    g = _load_graph(scope)
    cfg = load_kg_config()
    max_hops = int(cfg["max_query_hops"])
    cap = int(cfg["max_subgraph_nodes"])

    if kind == "neighbors":
        node = params["node"]
        hops = min(int(params.get("hops", 1)), max_hops)
        if node not in g:
            return {"kind": kind, "nodes": [], "edges": []}
        ego = nx.ego_graph(g.to_undirected(as_view=True), node, radius=hops)
        nodes = sorted(ego.nodes())[:cap]
        return {"kind": kind, "nodes": nodes}

    if kind == "path":
        a, b = params["node_a"], params["node_b"]
        try:
            path = nx.shortest_path(g.to_undirected(as_view=True), a, b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            path = []
        return {"kind": kind, "path": path[:cap]}

    if kind == "timeline_of":
        node = params["node"]
        events = (
            sorted(
                (n for n in g.successors(node) if g.nodes[n].get("kind") == "event"),
                key=lambda n: (g.nodes[n].get("chapter") or 0, n),
            )
            if node in g
            else []
        )
        return {
            "kind": kind,
            "events": [
                {
                    "id": e,
                    "chapter": g.nodes[e].get("chapter"),
                    "event_type": g.nodes[e].get("event_type"),
                }
                for e in events
            ],
        }

    if kind == "subgraph":
        lo = int(params.get("chapter_from", 0))
        hi = int(params.get("chapter_to", 10**9))
        nodes = [
            n
            for n, d in g.nodes(data=True)
            if d.get("kind") != "event" or (lo <= (d.get("chapter") or -1) <= hi)
        ]
        return {"kind": kind, "nodes": sorted(nodes)[:cap]}

    if kind == "events_between":
        a, b = params["node_a"], params["node_b"]
        try:
            path = nx.shortest_path(g.to_undirected(as_view=True), a, b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            path = []
        evs = sorted(
            (n for n in path if g.nodes.get(n, {}).get("kind") == "event"),
            key=lambda n: (g.nodes[n].get("chapter") or 0, n),
        )
        return {"kind": kind, "events": evs[:cap]}

    raise ValueError(f"unknown query kind {kind!r}")


def detect_contradictions(novel_path: str | Path) -> dict[str, Any]:
    """Detect tiered narrative contradictions over the KG (Req 4; P27/P28).

    **Pure and read-only:** loads the persisted graph (or rebuilds it in-RAM when
    the file is absent) and returns findings without mutating any state, memory,
    or file — so it is safe to call anywhere (P28). The single write action a
    contradiction can trigger lives in the separate ``apply_contradictions`` step.

    Hard tier — ``kg_dead_but_acts``: per entity, its events are ordered by
    chapter; a *terminal* event (death/sealed/departed, from config) at chapter X
    followed by any later action event at chapter Y > X — with no *recovery* event
    (revive/released) in between — is a logic contradiction that câu-chữ can't fix,
    so it is queued for a rewrite (Req 4.2, 4.4). The soft tier (same attribute,
    conflicting high-confidence values) is report-only and grows in a later task.
    """
    scope = Path(novel_path)
    g = _load_graph(scope)
    cfg = load_kg_config()
    terminal = {t.lower() for t in cfg["terminal_event_types"]}
    recovery = {r.lower() for r in cfg["recovery_event_types"]}

    hard: list[dict[str, Any]] = []
    for ent, d in g.nodes(data=True):
        if d.get("kind") != "entity":
            continue
        events = sorted(
            (
                (n, g.nodes[n])
                for n in g.successors(ent)
                if g.nodes[n].get("kind") == "event"
            ),
            # Secondary key on the node id keeps same-chapter ordering stable and
            # deterministic (parity with graph_model's event ordering); without it
            # a same-chapter terminal/action pair sorts arbitrarily.
            key=lambda x: (x[1].get("chapter") or 0, x[0]),
        )
        death_ch: int | None = None
        for _, ed in events:
            et = (ed.get("event_type") or "").lower()
            summary = (ed.get("summary") or "").lower()
            ch = ed.get("chapter") or 0
            if any(t in et or t in summary for t in terminal):
                death_ch = ch
            # Recovery is scanned across BOTH event_type and summary (parity with
            # the terminal check above); a recovery described only in the summary
            # would otherwise be missed, leaving a false kg_dead_but_acts.
            elif death_ch is not None and any(
                r in et or r in summary for r in recovery
            ):
                death_ch = None  # recovered — the terminal state no longer holds
            elif death_ch is not None and ch > death_ch:
                hard.append(
                    {
                        "code": "kg_dead_but_acts",
                        "affected_chapters": [ch],
                        "evidence": {
                            "entity": d.get("name"),
                            "death_chapter": death_ch,
                            "acted_chapter": ch,
                        },
                    }
                )
                break

    # --- Soft tier: same entity, same field, conflicting values (Req 4.3) ---
    soft: list[dict[str, Any]] = []
    min_conf = float(cfg.get("min_conflict_confidence", 0.7))

    for ent, d in g.nodes(data=True):
        if d.get("kind") != "entity":
            continue
        events_by_field: dict[str, list[tuple[int, str]]] = {}
        for n in g.successors(ent):
            ed = g.nodes[n]
            if ed.get("kind") != "event":
                continue
            et = (ed.get("event_type") or "").strip()
            ch = ed.get("chapter") or 0
            summary = (ed.get("summary") or "").strip()
            if et and ch and summary:
                events_by_field.setdefault(et, []).append((ch, summary))

        for field_name, entries in events_by_field.items():
            if len(entries) < 2:
                continue
            entries.sort(key=lambda x: x[0])
            for i in range(len(entries) - 1):
                ch_a, val_a = entries[i]
                ch_b, val_b = entries[i + 1]
                if val_a.lower() == val_b.lower():
                    continue
                gap = ch_b - ch_a
                if gap == 0:
                    confidence = 0.95
                elif gap <= 2:
                    confidence = 0.85
                elif gap <= 5:
                    confidence = 0.75
                else:
                    confidence = 0.5
                if confidence < min_conf:
                    continue
                soft.append({
                    "code": "kg_state_conflict",
                    "affected_chapters": [ch_a, ch_b],
                    "evidence": {
                        "entity": d.get("name"),
                        "field": field_name,
                        "value_a": val_a,
                        "chapter_a": ch_a,
                        "value_b": val_b,
                        "chapter_b": ch_b,
                        "confidence": confidence,
                    },
                })
                break

    return {"soft": soft, "hard": hard}


def apply_contradictions(
    novel_path: str | Path,
    state: dict[str, Any],
    hard: list[dict[str, Any]],
) -> dict[str, Any]:
    """Enqueue rewrite-queue entries for hard contradictions (Req 4.4).

    The separate *write* step: it takes the detected hard contradictions plus a
    serialised ``PipelineState`` payload and enqueues one ``rewrite_queue`` item
    per affected chapter through the existing editor path — **never** touching the
    review gate (Req 4.5). Idempotent by ``queue_id``: re-running with the same
    contradictions never duplicates a queue entry, so it is safe to call each sync.
    """
    from datetime import datetime, timezone

    from tools.novelkit_pipeline_tool import PipelineState

    ps = PipelineState.from_dict(state)
    enqueued = 0
    for c in hard:
        for ch in c.get("affected_chapters", []):
            # Best-effort parity with the rest of this module: a malformed
            # (non-int) chapter is skipped rather than crashing the enqueue.
            try:
                ch_int = int(ch)
            except (TypeError, ValueError):
                continue
            qid = f"rewrite_chapter_{ch_int:04d}_kg_{c['code']}"
            if any(q.get("queue_id") == qid for q in ps.creative.rewrite_queue):
                continue
            ps.creative.rewrite_queue.append(
                {
                    "queue_id": qid,
                    "kind": "rewrite",
                    "chapter": ch_int,
                    "reason_codes": ["kg_contradiction", c["code"]],
                    "priority": 15,
                    "attempt": 0,
                    "max_attempts": 3,
                    "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            enqueued += 1
    return {"state": ps.to_dict(), "enqueued": enqueued}


def graph_tool(action: str, **kwargs: Any) -> Any:
    """Dispatch entrypoint for the ``novelkit_graph`` tool (hub-and-spoke seam)."""
    if action == "build":
        return build(kwargs["novel_path"], through_chapter=kwargs.get("through_chapter"))
    if action == "export":
        return export(kwargs["novel_path"])
    if action == "query":
        return query(
            kwargs["novel_path"],
            kind=kwargs["kind"],
            **{
                k: v
                for k, v in kwargs.items()
                if k not in ("action", "novel_path", "kind")
            },
        )
    if action == "detect_contradictions":
        return detect_contradictions(kwargs["novel_path"])
    if action == "apply_contradictions":
        return apply_contradictions(
            kwargs["novel_path"], kwargs["state"], kwargs["hard"]
        )
    raise ValueError(f"unknown action {action!r}")


registry.register(
    "novelkit_graph",
    graph_tool,
    schema={
        "name": "novelkit_graph",
        "description": "Narrative knowledge graph: build/query/detect/export.",
        "input": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "novel_path": {"type": "string"},
            },
            "required": ["action", "novel_path"],
        },
        "output": {"type": "object"},
    },
    module=__name__,
)


__all__ = [
    "load_kg_config",
    "GRAPH_REL_PATH",
    "build",
    "export",
    "query",
    "detect_contradictions",
    "apply_contradictions",
    "graph_tool",
]
