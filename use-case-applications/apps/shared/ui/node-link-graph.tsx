/**
 * Node-link graph renderer — hand-rolled SVG, deterministic layout, NO dependency.
 *
 * An actual node-link diagram (drawn nodes + labeled edges in 2D), not stacked rows.
 * The data is tiny and fixed-shape (one customer's neighborhood ~8-12 nodes; the schema
 * ~5 type-nodes), so positions are computed deterministically — no physics sim, no
 * layout library, stable for screenshots. It matches the house inline-SVG idiom used
 * across the cards (household-strip, capability-cards, ask-graph-panel).
 *
 * FONT (per role): human-readable labels (names, "Account", "Advisor") render in the
 * UI SANS (--sans); code tokens (atlas:Customer, fibo:IndependentParty, …Shape) and
 * ontology property names on edges render in MONO (--mono). `isCodeToken()` decides.
 *
 * Two visual languages carry the kind-of-truth honesty as VISUAL STATE:
 *   - kind "live"   → solid node, green accent (--green): a per-customer fetched fact.
 *   - kind "schema" → neutral/structural (ink + --line), a distinct shape for class
 *                     nodes: the LOADED ontology, the same for every customer — NOT a
 *                     live-per-customer lookup, so it never wears the live-green.
 *
 * INCREMENT 2 READINESS: every node and edge carries a `highlight` and `dim` field
 * (defaulted false here, unused in Increment 1). The question-driven highlight pass
 * (Increment 2) adds state to this model — it does not rewrite the renderer.
 */

import React from "react";

/** Visual kind — drives the honesty treatment (live instance vs loaded schema). */
export type GraphKind = "live" | "schema";

/** Node shape — circles for instances, rounded-rects for ontology classes (Hive-style). */
export type NodeShape = "circle" | "rect";

/** Where a circle node's label sits relative to the node (rects always label inside). */
export type LabelAnchor = "below" | "above" | "left" | "right";

export interface GraphNode {
  id: string;
  label: string;
  /** Optional sub-label (e.g. "⊑ fibo:FinancialAccount" or "atlas:Customer"). */
  sublabel?: string;
  /** Ontology class node vs a concrete instance node. */
  type: "class" | "instance";
  kind: GraphKind;
  shape: NodeShape;
  x: number;
  y: number;
  /** Circle-node label placement (default "below"); set outward by the radial layout. */
  labelAnchor?: LabelAnchor;
  /** Increment-2 highlight/dim overlay state (driven by a real askGraph answer). */
  highlight?: boolean;
  dim?: boolean;
  /** Increment-2 honest count badge (e.g. "12 results", "3 types · 18 signals"). Only set
   *  where the real result shape carries an honest count — never fabricated. */
  badge?: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  /** The relationship label drawn beside the line (the Hive-style edge label). */
  label: string;
  kind: GraphKind;
  /** Increment-2 state (unused in Increment 1; defaults false). */
  highlight?: boolean;
  dim?: boolean;
}

export interface NodeLinkGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** SVG viewBox width / height — the layout helpers below produce coords in this space. */
  width?: number;
  height?: number;
  /** Accessible description of the diagram. */
  ariaLabel?: string;
}

/**
 * A string is a "code token" (→ mono) when it carries an ontology identifier shape:
 * a prefixed name (atlas:Customer / fibo:…), a subClassOf glyph (⊑ …), or a SHACL
 * shape name (…Shape). Everything else (human names, "Account", "2 members") is sans.
 * This matches the rest of the UI, where code identifiers are mono and prose is sans.
 */
function isCodeToken(s?: string): boolean {
  if (!s) return false;
  return /[A-Za-z]+:|⊑|Shape/.test(s);
}
function fontFor(s?: string): string {
  return isCodeToken(s) ? "var(--mono)" : "var(--sans)";
}

/** Rough text-width estimate (px) for adaptive rect sizing — mono is wider than sans. */
function textWidth(s: string, fontPx: number, mono: boolean): number {
  return s.length * fontPx * (mono ? 0.62 : 0.56);
}

const CIRCLE_R = 22;
const RECT_H = 48;
const RECT_MIN_W = 124;
const RECT_PAD = 22;

/** Rounded-rect width sized to the longer of its label / sublabel (class nodes). */
function rectWidth(node: GraphNode): number {
  const w1 = textWidth(node.label, 10.5, isCodeToken(node.label));
  const w2 = node.sublabel ? textWidth(node.sublabel, 8, isCodeToken(node.sublabel)) : 0;
  return Math.max(RECT_MIN_W, Math.ceil(Math.max(w1, w2)) + RECT_PAD);
}

/** Per-kind node styling. live = green/solid; schema = neutral/structural. The honesty
 *  visual is PRESERVED + sharpened here: live nodes carry the green accent, schema nodes
 *  stay neutral/structural — never green. (Restyle = look, not truth.) */
function nodeStyle(node: GraphNode): { fill: string; stroke: string; text: string; strokeWidth: number } {
  if (node.kind === "live") {
    return {
      fill: "var(--green-bg)",
      stroke: "var(--green)",
      text: "var(--ink)",
      strokeWidth: node.highlight ? 2.6 : 1.6,
    };
  }
  return {
    fill: "var(--panel)",
    stroke: "var(--line)",
    text: "var(--ink-2)",
    strokeWidth: node.highlight ? 2.6 : 1.25,
  };
}

function edgeStroke(edge: GraphEdge): string {
  return edge.kind === "live" ? "var(--green)" : "var(--ink-3)";
}

/** Half-extent of a node toward a given direction (for trimming edges to the boundary). */
function nodeRadiusToward(node: GraphNode, ux: number, uy: number): number {
  if (node.shape === "circle") return CIRCLE_R;
  // rect: distance from center to the boundary along (ux,uy)
  const hw = rectWidth(node) / 2;
  const hh = RECT_H / 2;
  const tx = Math.abs(ux) < 1e-6 ? Infinity : hw / Math.abs(ux);
  const ty = Math.abs(uy) < 1e-6 ? Infinity : hh / Math.abs(uy);
  return Math.min(tx, ty);
}

function NodeShapeEl({ node, dragging }: { node: GraphNode; dragging: boolean }) {
  const s = nodeStyle(node);
  // House idiom: the emphasized node carries a soft ring (echoing .av's
  // `box-shadow: 0 0 0 3px var(--green-bg)`) — here as an SVG halo while dragging or
  // when the layout marks it the hub (a circle instance with no labelAnchor override).
  const haloFill = node.kind === "live" ? "var(--green-bg)" : "var(--line-2)";
  if (node.shape === "rect") {
    const w = rectWidth(node);
    return (
      <>
        {dragging && (
          <rect
            x={node.x - w / 2 - 3}
            y={node.y - RECT_H / 2 - 3}
            width={w + 6}
            height={RECT_H + 6}
            rx={12}
            fill="none"
            stroke={haloFill}
            strokeWidth={5}
          />
        )}
        <rect
          x={node.x - w / 2}
          y={node.y - RECT_H / 2}
          width={w}
          height={RECT_H}
          rx={10}
          fill={s.fill}
          stroke={s.stroke}
          strokeWidth={s.strokeWidth}
        />
      </>
    );
  }
  return (
    <>
      {dragging && <circle cx={node.x} cy={node.y} r={CIRCLE_R + 4} fill="none" stroke={haloFill} strokeWidth={5} />}
      <circle cx={node.x} cy={node.y} r={CIRCLE_R} fill={s.fill} stroke={s.stroke} strokeWidth={s.strokeWidth} />
    </>
  );
}

/** An honest count badge — a small accent pill above the node. Rendered only when a node
 *  carries `badge` text (set ONLY where the real result shape carries an honest count). */
function BadgeEl({ node }: { node: GraphNode }) {
  if (!node.badge) return null;
  const w = textWidth(node.badge, 9, false) + 14;
  const half = node.shape === "rect" ? RECT_H / 2 : CIRCLE_R;
  const by = node.y - half - 13;
  return (
    <g style={{ pointerEvents: "none" }}>
      <rect
        x={node.x - w / 2}
        y={by - 9}
        width={w}
        height={17}
        rx={8.5}
        fill="var(--accent-bg)"
        stroke="var(--accent)"
        strokeWidth={0.85}
      />
      <text x={node.x} y={by + 3} textAnchor="middle" fontSize="9.5" fontWeight={600} fontFamily="var(--sans)" fill="var(--accent-strong)">
        {node.badge}
      </text>
    </g>
  );
}

export function NodeLinkGraph({
  nodes,
  edges,
  width = 560,
  height = 360,
  ariaLabel = "Node-link graph",
}: NodeLinkGraphProps) {
  const svgRef = React.useRef<SVGSVGElement | null>(null);

  // DRAG: positions live in component state, SEEDED from the deterministic layout each
  // mount. Re-seeded whenever the incoming node set changes (a different customer). This
  // is the reset-on-reload behaviour: dragged positions are session-only, never persisted
  // (no storage). Increment-2 highlight/dim stay on the node objects — position state
  // lives ALONGSIDE them here, so both coexist on the same model.
  const seedKey = nodes.map((n) => n.id).join("|");
  const [pos, setPos] = React.useState<Record<string, { x: number; y: number }>>({});
  React.useEffect(() => {
    const seed: Record<string, { x: number; y: number }> = {};
    for (const n of nodes) seed[n.id] = { x: n.x, y: n.y };
    setPos(seed);
    // re-seed on a new node set (new customer) — resets exploration to the clean layout
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedKey]);

  const [dragId, setDragId] = React.useState<string | null>(null);

  // Effective position: dragged/state position if present, else the prop seed.
  const at = (n: GraphNode) => pos[n.id] ?? { x: n.x, y: n.y };
  const live = (n: GraphNode): GraphNode => ({ ...n, ...at(n) });

  const byId = React.useMemo(() => {
    const m: Record<string, GraphNode> = {};
    for (const n of nodes) m[n.id] = live(n);
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, pos]);

  // Map a pointer event to SVG viewBox coordinates (so drag tracks under the cursor
  // regardless of the SVG's responsive on-page size). Uses the inverse screen CTM.
  const toSvg = (clientX: number, clientY: number): { x: number; y: number } => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const p = svg.createSVGPoint();
    p.x = clientX;
    p.y = clientY;
    const r = p.matrixTransform(ctm.inverse());
    return { x: r.x, y: r.y };
  };

  const onPointerDownNode = (id: string) => (e: React.PointerEvent) => {
    e.preventDefault();
    (e.target as Element).setPointerCapture?.(e.pointerId);
    setDragId(id);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragId) return;
    const { x, y } = toSvg(e.clientX, e.clientY);
    // clamp inside the canvas so a node can't be dragged out of view
    const cx = Math.max(28, Math.min(width - 28, x));
    const cy = Math.max(28, Math.min(height - 28, y));
    setPos((prev) => ({ ...prev, [dragId]: { x: cx, y: cy } }));
  };
  const endDrag = (e: React.PointerEvent) => {
    if (dragId) (e.target as Element).releasePointerCapture?.(e.pointerId);
    setDragId(null);
  };

  return (
    <svg
      ref={svgRef}
      className="nlg"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      role="img"
      aria-label={`${ariaLabel} — nodes are draggable; reload resets the layout`}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerLeave={endDrag}
      style={{ display: "block", maxWidth: "100%", height: "auto", touchAction: "none" }}
    >
      <defs>
        {/* Directed-edge arrowheads, one per kind so the marker inherits the edge colour
            (live = green, schema = neutral ink). Refines the "drawn relationship" look. */}
        <marker id="nlg-arrow-live" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="var(--green)" />
        </marker>
        <marker id="nlg-arrow-schema" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)" />
        </marker>
      </defs>

      {/* Edges first (drawn under nodes) — line + arrowhead + the relationship label
          BESIDE the line. All endpoints recompute from the LIVE (possibly dragged) positions. */}
      {edges.map((e, i) => {
        const from = byId[e.from];
        const to = byId[e.to];
        if (!from || !to) return null;
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const ux = dx / len;
        const uy = dy / len;
        // Trim each endpoint to its node boundary so the line meets the shape cleanly.
        const x1 = from.x + ux * (nodeRadiusToward(from, ux, uy) + 2);
        const y1 = from.y + uy * (nodeRadiusToward(from, ux, uy) + 2);
        const x2 = to.x - ux * (nodeRadiusToward(to, -ux, -uy) + 7);
        const y2 = to.y - uy * (nodeRadiusToward(to, -ux, -uy) + 7);

        // Label biased toward the TARGET (t=0.58, away from a hub/center node) and OFFSET
        // PERPENDICULAR to the line — beside the edge, never on the hub's text. (Bug-1 fix
        // preserved; positions are live so the label tracks a dragged node.)
        const t = 0.58;
        const baseX = x1 + (x2 - x1) * t;
        const baseY = y1 + (y2 - y1) * t;
        const PERP = 11;
        const lx = baseX + -uy * PERP;
        const ly = baseY + ux * PERP;

        const stroke = edgeStroke(e);
        const op = e.dim ? 0.32 : 1;
        const labW = textWidth(e.label, 9.5, true); // edge labels are property names → mono
        const marker = e.kind === "live" ? "url(#nlg-arrow-live)" : "url(#nlg-arrow-schema)";
        return (
          <g key={`e-${i}`} opacity={op}>
            <line
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={stroke}
              strokeWidth={e.highlight ? 2.4 : 1.4}
              strokeLinecap="round"
              markerEnd={marker}
            />
            {/* rounded pill backing keeps the label legible where it sits near the line */}
            <rect
              x={lx - labW / 2 - 5}
              y={ly - 8.5}
              width={labW + 10}
              height={16}
              rx={8}
              fill="var(--panel)"
              stroke="var(--line-2)"
              strokeWidth={0.75}
            />
            <text x={lx} y={ly + 3} textAnchor="middle" fontSize="9.5" fontFamily="var(--mono)" fill="var(--ink-3)">
              {e.label}
            </text>
          </g>
        );
      })}

      {/* Nodes on top. Rects label INSIDE (class nodes); circles label at an outward
          ANCHOR (set by the layout) so instance labels never sit on edges or the hub.
          Each node group is the drag handle (pointer-down starts a drag). */}
      {nodes.map((n0) => {
        const n = byId[n0.id];
        const s = nodeStyle(n);
        const op = n.dim ? 0.4 : 1;
        const isDragging = dragId === n.id;
        const handlers = {
          onPointerDown: onPointerDownNode(n.id),
          style: { cursor: isDragging ? "grabbing" : "grab" } as React.CSSProperties,
        };

        if (n.shape === "rect") {
          return (
            <g key={`n-${n.id}`} opacity={op} {...handlers}>
              <NodeShapeEl node={n} dragging={isDragging} />
              <BadgeEl node={n} />
              <text
                x={n.x}
                y={n.sublabel ? n.y - 3 : n.y + 3}
                textAnchor="middle"
                fontSize="10.5"
                fontWeight={600}
                fontFamily={fontFor(n.label)}
                fill={s.text}
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {n.label}
              </text>
              {n.sublabel && (
                <text
                  x={n.x}
                  y={n.y + 12}
                  textAnchor="middle"
                  fontSize="8"
                  fontFamily={fontFor(n.sublabel)}
                  fill="var(--ink-3)"
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {n.sublabel}
                </text>
              )}
            </g>
          );
        }

        // circle — label placed outward per labelAnchor (default below)
        const anchor: LabelAnchor = n.labelAnchor ?? "below";
        const gap = CIRCLE_R + 12;
        let tx = n.x;
        let ty = n.y + gap;
        let textAnchor: "middle" | "start" | "end" = "middle";
        if (anchor === "above") {
          ty = n.y - gap - (n.sublabel ? 10 : 0);
        } else if (anchor === "right") {
          tx = n.x + gap;
          ty = n.y - (n.sublabel ? 4 : -3);
          textAnchor = "start";
        } else if (anchor === "left") {
          tx = n.x - gap;
          ty = n.y - (n.sublabel ? 4 : -3);
          textAnchor = "end";
        }
        return (
          <g key={`n-${n.id}`} opacity={op} {...handlers}>
            <NodeShapeEl node={n} dragging={isDragging} />
            <BadgeEl node={n} />
            <text
              x={tx}
              y={ty}
              textAnchor={textAnchor}
              fontSize="11"
              fontWeight={600}
              fontFamily={fontFor(n.label)}
              fill={s.text}
              style={{ pointerEvents: "none", userSelect: "none" }}
            >
              {n.label}
            </text>
            {n.sublabel && (
              <text
                x={tx}
                y={ty + 12}
                textAnchor={textAnchor}
                fontSize="8.5"
                fontFamily={fontFor(n.sublabel)}
                fill="var(--ink-3)"
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {n.sublabel}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/**
 * Deterministic radial layout — a center node with its neighbors evenly spaced on a
 * ring. Returns positions AND per-neighbor label anchors (outward: right-half → right,
 * left-half → left, top → above, bottom → below) so circle labels radiate outward and
 * never collide with the hub or the edges. Pure function of input order → stable.
 *
 * `startDeg` offsets the ring so edges are not axis-aligned (diagonal placement keeps
 * horizontal edge labels off the hub's text — part of the bug-1 fix).
 */
export function radialLayout<T extends { id: string }>(
  center: T,
  neighbors: T[],
  opts?: { width?: number; height?: number; radius?: number; startDeg?: number },
): {
  cx: number;
  cy: number;
  positions: Record<string, { x: number; y: number }>;
  anchors: Record<string, LabelAnchor>;
} {
  const width = opts?.width ?? 560;
  const height = opts?.height ?? 360;
  const radius = opts?.radius ?? Math.min(width, height) / 2 - 78;
  const startDeg = opts?.startDeg ?? -45; // diagonal start → corners, not cardinal axes
  const cx = width / 2;
  const cy = height / 2;
  const positions: Record<string, { x: number; y: number }> = { [center.id]: { x: cx, y: cy } };
  const anchors: Record<string, LabelAnchor> = { [center.id]: "below" };
  const n = neighbors.length || 1;
  neighbors.forEach((node, i) => {
    const angle = (startDeg * Math.PI) / 180 + (2 * Math.PI * i) / n;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    positions[node.id] = { x, y };
    // Outward anchor: dominant direction decides where the label sits.
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    let anchor: LabelAnchor;
    if (Math.abs(cos) >= Math.abs(sin)) {
      anchor = cos >= 0 ? "right" : "left";
    } else {
      anchor = sin >= 0 ? "below" : "above";
    }
    anchors[node.id] = anchor;
  });
  return { cx, cy, positions, anchors };
}
