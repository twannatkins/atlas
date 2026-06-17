/**
 * Schema graph card — the loaded ATLAS ontology as a node-link diagram.
 *
 * The TYPE-level model (the Hive "Ontology Studio" view): the ontology classes and
 * the relationships between them, drawn as nodes + labeled edges. This is the SAME
 * for every customer — it is the loaded schema, NOT a per-customer query — so it is
 * rendered in the LOADED-SCHEMA visual treatment (neutral/structural, rounded-rect
 * class nodes, a "model · FIBO 2024 Q3" header) and deliberately wears NO live-green
 * pill: putting one here would overclaim the schema as live-queried.
 *
 * Shared by both UIs (one ontology truth, no drift) — wholesale places it above
 * Ask-the-graph on My Book; wealth places it above the /conversations panel.
 *
 * Every node and edge traces to a real Workshop 1 ontology file — nothing invented:
 *   - atlas:Customer ⊑ fibo:IndependentParty,  atlas:Account ⊑ fibo:FinancialAccount,
 *     atlas:Advisor ⊑ fibo:FunctionalRole  → atlas-fibo-alignment.ttl (bindings 1/2/5)
 *   - atlas:WealthSignal, atlas:Household (bank-specific, no FIBO) → documented in the
 *     same file's "no FIBO counterpart" list
 *   - hasAccount / memberOf / producesSignal / coveringAdvisor(advisesCustomer)
 *     → atlas-core.ttl object properties
 *   - the WealthSignal node annotates atlas:WealthSignalTypeShape → atlas-shapes.ttl
 */

import React from "react";
import { NodeLinkGraph, GraphNode, GraphEdge } from "./node-link-graph";
import { SchemaHighlightState, edgeKey } from "./schema-graph-highlight";

/**
 * Balanced Hive-style 2D arrangement of the real type-nodes (deterministic, no layout
 * lib). atlas:Customer is the hub at the center of a 620×380 viewBox; the four related
 * classes sit at evenly-spread compass points around it (top-right Account, right
 * Household, bottom-right WealthSignal, left Advisor) so no column crowds and every edge
 * has room for its label. Coordinates chosen so the adaptive rect widths don't collide.
 */
const CW = 620;
const CH = 380;
const SCHEMA_NODES: GraphNode[] = [
  {
    id: "Customer",
    label: "atlas:Customer",
    sublabel: "⊑ fibo:IndependentParty",
    type: "class",
    kind: "schema",
    shape: "rect",
    x: CW / 2,
    y: CH / 2,
  },
  {
    id: "Account",
    label: "atlas:Account",
    sublabel: "⊑ fibo:FinancialAccount",
    type: "class",
    kind: "schema",
    shape: "rect",
    x: 470,
    y: 78,
  },
  {
    id: "Household",
    label: "atlas:Household",
    sublabel: "bank-specific",
    type: "class",
    kind: "schema",
    shape: "rect",
    x: 510,
    y: 190,
  },
  {
    id: "WealthSignal",
    label: "atlas:WealthSignal",
    sublabel: "SHACL · WealthSignalTypeShape",
    type: "class",
    kind: "schema",
    shape: "rect",
    x: 440,
    y: 302,
  },
  {
    id: "Advisor",
    label: "atlas:Advisor",
    sublabel: "⊑ fibo:FunctionalRole",
    type: "class",
    kind: "schema",
    shape: "rect",
    x: 120,
    y: 300,
  },
];

const SCHEMA_EDGES: GraphEdge[] = [
  { from: "Customer", to: "Account", label: "hasAccount", kind: "schema" },
  { from: "Customer", to: "Household", label: "memberOf", kind: "schema" },
  { from: "Customer", to: "WealthSignal", label: "producesSignal", kind: "schema" },
  { from: "Advisor", to: "Customer", label: "advisesCustomer", kind: "schema" },
];

interface SchemaGraphCardProps {
  perspective?: "wholesale" | "wealth";
  /**
   * Increment-2 overlay: highlight/count state derived from a REAL askGraph answer
   * (deriveSchemaHighlight). When `active`, the traversed nodes/edges highlight and the
   * rest dim; honest count badges annotate the nodes the real result shape supports. When
   * absent/inactive, the graph renders in its neutral resting state (the loaded model).
   * This is a query-response OVERLAY — it does NOT change the schema's loaded-model nature.
   */
  highlight?: SchemaHighlightState | null;
}

export function SchemaGraphCard({ perspective = "wholesale", highlight }: SchemaGraphCardProps) {
  // The advisory edge is the same ontology relationship; only the directional label
  // differs by lens (coveringAdvisor on the wholesale side, advisesCustomer on the
  // wealth side) — exactly as the grounding-card rows already do.
  const baseEdges =
    perspective === "wholesale"
      ? SCHEMA_EDGES.map((e) =>
          e.from === "Advisor" && e.to === "Customer"
            ? { ...e, from: "Customer", to: "Advisor", label: "coveringAdvisor" }
            : e,
        )
      : SCHEMA_EDGES;

  const active = !!highlight?.active;
  const hlNodes = new Set(highlight?.nodeIds ?? []);
  const hlEdges = new Set(highlight?.edgeKeys ?? []);
  const badges = highlight?.badges ?? {};

  // Apply the overlay onto the model's existing highlight/dim/badge fields. When active,
  // mapped nodes/edges highlight and the rest dim; otherwise everything renders normally
  // (resting). Pure transform — no data changes, only overlay state.
  const nodes: GraphNode[] = SCHEMA_NODES.map((n) => ({
    ...n,
    highlight: active && hlNodes.has(n.id),
    dim: active && !hlNodes.has(n.id),
    badge: active ? badges[n.id] : undefined,
  }));
  const edges: GraphEdge[] = baseEdges.map((e) => {
    const k = edgeKey(e.from, e.to);
    return { ...e, highlight: active && hlEdges.has(k), dim: active && !hlEdges.has(k) };
  });

  return (
    <div className="card">
      <div className="card-h">
        <span className="t">The model — ATLAS ontology</span>
        {/* LOADED-SCHEMA provenance label — the same "model FIBO 2024 Q3" wording the
            grounding-card rows use. Deliberately NOT a live pill: the schema is the
            loaded ontology, identical for every customer, not a live-per-customer query.
            The highlight overlay below does NOT change this — it shows which part of the
            loaded model a real query traversed. */}
        <span className="meta">model · FIBO 2024 Q3</span>
      </div>
      <p className="card-note" style={{ marginTop: 0, borderTop: "none", paddingTop: 0 }}>
        The loaded ontology — the same for every customer, not a live lookup. Classes and the
        relationships between them, drawn from the Workshop&nbsp;1 ontology (atlas-core,
        atlas-fibo-alignment, atlas-shapes).
      </p>
      <NodeLinkGraph
        nodes={nodes}
        edges={edges}
        width={CW}
        height={CH}
        ariaLabel="ATLAS ontology schema: classes and their relationships"
      />
      {active ? (
        <p className="card-note" style={{ marginTop: 6, fontSize: 10.5 }}>
          Highlighted: the part of the model your last question actually traversed · counts are
          the real result.
        </p>
      ) : highlight?.message ? (
        // Honest no-map note: a real answer that doesn't map to the 5-type model view.
        <p className="card-note" style={{ marginTop: 6, fontSize: 10.5 }}>
          {highlight.message}
        </p>
      ) : (
        <p className="card-note" style={{ marginTop: 6, fontSize: 10.5 }}>
          Drag any class to explore the model · ask a question below to light up the path it
          traverses · the layout resets on reload.
        </p>
      )}
    </div>
  );
}
