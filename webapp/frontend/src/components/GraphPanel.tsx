import { useEffect, useMemo, useState } from "react";
import { ShareNetwork, WarningCircle } from "@phosphor-icons/react";
import { api } from "../api";
import { useT } from "../i18n/I18nProvider";
import type { GraphNode, GraphResponse } from "../types";

// --- Layout constants (SVG viewBox space) ---
const W = 900;
const H = 620;
const PAD = 40;

// Color per node kind. Unknown kinds fall back to a neutral slate.
const KIND_COLORS: Record<string, string> = {
  entity: "#6366f1", // indigo
  relationship: "#10b981", // emerald
  event: "#f59e0b", // amber
  arc: "#8b5cf6", // violet
  volume: "#ec4899", // pink
};
const DEFAULT_COLOR = "#94a3b8";

function kindColor(kind: string): string {
  return KIND_COLORS[kind] ?? DEFAULT_COLOR;
}

// Deterministic 32-bit hash (FNV-1a) so layout is stable across renders.
function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Read a numeric chapter off a node regardless of string/number encoding.
function nodeChapter(node: GraphNode): number | null {
  const raw = node.chapter;
  const n = typeof raw === "number" ? raw : Number(raw);
  return Number.isFinite(n) ? n : null;
}

function nodeName(node: GraphNode): string | null {
  return typeof node.name === "string" ? node.name : null;
}

type Pos = { x: number; y: number };

/**
 * Deterministic light force-directed layout. Positions are computed once over
 * the FULL graph (not the filtered subset) so nodes keep their place while the
 * user toggles filters. No randomness — initial placement is seeded by node id.
 */
function computeLayout(nodes: GraphNode[], edges: { s: string; t: string }[]): Map<string, Pos> {
  const pos = new Map<string, Pos>();
  const n = nodes.length;
  if (n === 0) return pos;

  nodes.forEach((node) => {
    const h = hashStr(node.id);
    const angle = (h % 360) * (Math.PI / 180);
    const radius = 40 + (((h >>> 9) % 100) / 100) * Math.min(W, H) * 0.42;
    pos.set(node.id, {
      x: W / 2 + Math.cos(angle) * radius,
      y: H / 2 + Math.sin(angle) * radius,
    });
  });

  const liveEdges = edges.filter((e) => pos.has(e.s) && pos.has(e.t));
  const iterations = n > 150 ? 150 : 260;
  const repulsion = 2600;
  const springK = 0.02;
  const springLen = 95;

  for (let it = 0; it < iterations; it += 1) {
    const disp = new Map<string, Pos>();
    nodes.forEach((node) => disp.set(node.id, { x: 0, y: 0 }));

    // Repulsion between every pair (O(n^2), bounded by the iteration cap above).
    for (let i = 0; i < n; i += 1) {
      const ni = nodes[i];
      const a = pos.get(ni.id) as Pos;
      for (let j = i + 1; j < n; j += 1) {
        const nj = nodes[j];
        const b = pos.get(nj.id) as Pos;
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist2 = dx * dx + dy * dy;
        if (dist2 < 0.01) {
          // Coincident nodes: nudge apart deterministically by id hash.
          dx = (hashStr(ni.id + "#x") % 10) - 5 + 0.5;
          dy = (hashStr(nj.id + "#y") % 10) - 5 + 0.5;
          dist2 = dx * dx + dy * dy + 0.01;
        }
        const dist = Math.sqrt(dist2);
        const force = repulsion / dist2;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const da = disp.get(ni.id) as Pos;
        const db = disp.get(nj.id) as Pos;
        da.x += fx;
        da.y += fy;
        db.x -= fx;
        db.y -= fy;
      }
    }

    // Spring attraction along edges.
    for (const e of liveEdges) {
      const a = pos.get(e.s) as Pos;
      const b = pos.get(e.t) as Pos;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const pull = (dist - springLen) * springK;
      const fx = (dx / dist) * pull;
      const fy = (dy / dist) * pull;
      const da = disp.get(e.s) as Pos;
      const db = disp.get(e.t) as Pos;
      da.x -= fx;
      da.y -= fy;
      db.x += fx;
      db.y += fy;
    }

    // Apply displacement with cooling, gentle gravity, and frame clamping.
    const cool = 1 - it / iterations;
    const maxStep = 30 * cool + 2;
    nodes.forEach((node) => {
      const p = pos.get(node.id) as Pos;
      const d = disp.get(node.id) as Pos;
      let dx = d.x;
      let dy = d.y;
      const dlen = Math.sqrt(dx * dx + dy * dy) || 1;
      if (dlen > maxStep) {
        dx = (dx / dlen) * maxStep;
        dy = (dy / dlen) * maxStep;
      }
      p.x += dx + (W / 2 - p.x) * 0.01;
      p.y += dy + (H / 2 - p.y) * 0.01;
      p.x = Math.max(PAD, Math.min(W - PAD, p.x));
      p.y = Math.max(PAD, Math.min(H - PAD, p.y));
    });
  }

  return pos;
}

export function GraphPanel({ novel }: { novel: string }) {
  const t = useT();
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state.
  const [disabledKinds, setDisabledKinds] = useState<Set<string>>(new Set());
  const [chapterMin, setChapterMin] = useState("");
  const [chapterMax, setChapterMax] = useState("");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setData(null);
    api
      .graph(novel)
      .then((res) => {
        if (alive) setData(res);
      })
      .catch((e: unknown) => {
        if (alive) setError((e as Error).message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [novel]);

  const nodes = useMemo<GraphNode[]>(() => data?.graph?.nodes ?? [], [data]);
  const links = useMemo(() => data?.graph?.links ?? [], [data]);

  // Distinct kinds present, for the kind filter checkboxes.
  const kinds = useMemo(() => {
    const set = new Set<string>();
    nodes.forEach((n) => set.add(n.kind));
    return [...set].sort();
  }, [nodes]);

  // Layout depends only on the full graph (stable while filtering).
  const layout = useMemo(() => {
    const edges = links.map((l) => ({ s: String(l.source), t: String(l.target) }));
    return computeLayout(nodes, edges);
  }, [nodes, links]);

  // Node ids highlighted by hard contradictions.
  const contradictionIds = useMemo(() => {
    const set = new Set<string>();
    const hard = data?.contradictions?.hard ?? [];
    if (hard.length === 0) return set;
    for (const c of hard) {
      const entity = c.evidence?.entity;
      const chapters = new Set(c.affected_chapters ?? []);
      for (const n of nodes) {
        if (n.kind === "entity" && entity && nodeName(n) === entity) {
          set.add(n.id);
        } else if (n.kind === "event") {
          const ch = nodeChapter(n);
          if (ch != null && chapters.has(ch)) set.add(n.id);
        }
      }
    }
    return set;
  }, [data, nodes]);

  // Visible nodes after applying kind + chapter-range filters.
  const visibleIds = useMemo(() => {
    const min = chapterMin.trim() === "" ? null : Number(chapterMin);
    const max = chapterMax.trim() === "" ? null : Number(chapterMax);
    const set = new Set<string>();
    for (const n of nodes) {
      if (disabledKinds.has(n.kind)) continue;
      if (n.kind === "event") {
        const ch = nodeChapter(n);
        if (ch != null) {
          if (min != null && Number.isFinite(min) && ch < min) continue;
          if (max != null && Number.isFinite(max) && ch > max) continue;
        }
      }
      set.add(n.id);
    }
    return set;
  }, [nodes, disabledKinds, chapterMin, chapterMax]);

  const visibleNodes = useMemo(
    () => nodes.filter((n) => visibleIds.has(n.id)),
    [nodes, visibleIds],
  );
  const visibleLinks = useMemo(
    () =>
      links.filter(
        (l) => visibleIds.has(String(l.source)) && visibleIds.has(String(l.target)),
      ),
    [links, visibleIds],
  );

  function toggleKind(kind: string) {
    setDisabledKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="panel">
        <div className="muted">{t("graph.loading")}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <div className="error">{t("graph.error", { message: error })}</div>
      </div>
    );
  }

  if (!data || !data.exists || !data.graph || nodes.length === 0) {
    return (
      <div className="panel">
        <div className="section-title icon-label">
          <ShareNetwork size={16} weight="light" /> {t("graph.title")}
        </div>
        <div className="muted">{t("graph.empty")}</div>
      </div>
    );
  }

  const hardCount = data.contradictions?.hard?.length ?? 0;
  const meta = data.metadata;

  return (
    <div className="panel">
      <div className="spread">
        <div className="section-title icon-label">
          <ShareNetwork size={16} weight="light" /> {t("graph.title")}
        </div>
        {meta && (
          <span className="muted small">
            {t("graph.stats", {
              nodes: meta.node_count,
              edges: meta.edge_count,
              chapter: meta.through_chapter,
            })}
          </span>
        )}
      </div>

      {hardCount > 0 && (
        <div className="error banner" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <WarningCircle size={15} weight="light" /> {t("graph.contradictions", { count: hardCount })}
        </div>
      )}

      {/* --- Filters --- */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          alignItems: "center",
          margin: "8px 0 12px",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <span className="muted small">{t("graph.filterKind")}</span>
          {kinds.map((k) => (
            <label
              key={k}
              className="inline small"
              style={{ display: "flex", alignItems: "center", gap: 5, cursor: "pointer" }}
            >
              <input
                type="checkbox"
                checked={!disabledKinds.has(k)}
                onChange={() => toggleKind(k)}
              />
              <span
                aria-hidden="true"
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: kindColor(k),
                  display: "inline-block",
                }}
              />
              {t(`graph.kind.${k}`)}
            </label>
          ))}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className="muted small">{t("graph.filterChapter")}</span>
          <input
            type="number"
            value={chapterMin}
            placeholder={t("graph.min")}
            onChange={(e) => setChapterMin(e.target.value)}
            style={{ width: 68 }}
          />
          <span className="muted">–</span>
          <input
            type="number"
            value={chapterMax}
            placeholder={t("graph.max")}
            onChange={(e) => setChapterMax(e.target.value)}
            style={{ width: 68 }}
          />
        </div>
      </div>

      {/* --- Graph --- */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={t("graph.title")}
        style={{
          width: "100%",
          height: "auto",
          maxHeight: "70vh",
          background: "rgba(148, 163, 184, 0.06)",
          borderRadius: 12,
          border: "1px solid rgba(148, 163, 184, 0.18)",
        }}
      >
        {visibleLinks.map((l, i) => {
          const a = layout.get(String(l.source));
          const b = layout.get(String(l.target));
          if (!a || !b) return null;
          return (
            <line
              key={`${String(l.source)}-${String(l.target)}-${l.key ?? i}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="rgba(148, 163, 184, 0.45)"
              strokeWidth={1}
            />
          );
        })}
        {visibleNodes.map((n) => {
          const p = layout.get(n.id);
          if (!p) return null;
          const flagged = contradictionIds.has(n.id);
          const name = nodeName(n);
          const r = n.kind === "entity" ? 7 : 5;
          return (
            <g key={n.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={r}
                fill={kindColor(n.kind)}
                stroke={flagged ? "#ef4444" : "rgba(15, 23, 42, 0.35)"}
                strokeWidth={flagged ? 3 : 1}
              >
                <title>{name ?? n.id}</title>
              </circle>
              {n.kind === "entity" && name && (
                <text
                  x={p.x + r + 3}
                  y={p.y + 3}
                  fontSize={10}
                  fill="currentColor"
                  style={{ pointerEvents: "none" }}
                >
                  {name}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
