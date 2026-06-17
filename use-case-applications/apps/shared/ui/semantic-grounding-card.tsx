/**
 * Semantic grounding card — the FIBO-aligned model this customer instantiates.
 *
 * The card teaches kind-of-truth, so it must be precise about its own. It holds
 * TWO distinct truths and never flattens them into one:
 *
 *   1. INSTANCE (live) — which accounts / household members / signals / advisor
 *      THIS customer actually has. Fetched per-customer from the graph, so the
 *      green `.lab-live` "live" pill is truthful here.
 *   2. SCHEMA (loaded model) — the atlas→FIBO subClassOf alignment
 *      (atlas:Account ⊑ fibo:FinancialAccount). This is the faithful LOADED
 *      ontology (FIBO 2024 Q3 Production Release), the SAME for every customer —
 *      NOT queried live per customer. It is labelled as ontology-version
 *      provenance, never with a "live" pill that would imply per-customer
 *      alignment querying.
 *
 * Shared by both ATLAS UIs (one component, two call sites): the ontology truth
 * lives in exactly one place so the two apps cannot drift. Each app maps its own
 * fetched data into the props below and passes its own <ProvenanceBadge> via the
 * `signalProvenance` slot (literal reuse of each app's existing component).
 *
 * Renders ONLY the real loaded model (WS1 atlas-core + atlas-fibo-alignment +
 * atlas-shapes). Nothing here is invented: every class/edge shown is in the
 * ontology, and a row appears only when that data is actually present for the
 * customer (same conditional discipline as the existing cards).
 */

import React from "react";
import { NodeLinkGraph, GraphNode, GraphEdge, radialLayout } from "./node-link-graph";

interface SemanticGroundingCardProps {
  /** This customer's label — the center node of the instance graph. */
  customerLabel?: string;
  /** Accounts present for this customer (Customer —hasAccount→ Account). */
  hasAccounts?: boolean;
  accountCount?: number;
  /** Household present (Customer —memberOf→ Household). */
  hasHousehold?: boolean;
  householdMemberCount?: number;
  /** Wealth signals present (Customer —producesSignal→ WealthSignal). */
  hasSignals?: boolean;
  signalCount?: number;
  /** Advisory coverage present (AdvisoryRelationship —coveringAdvisor→ Advisor). */
  hasAdvisory?: boolean;
  advisorLabel?: string;
  /**
   * Each app's own <ProvenanceBadge> for the SHACL-shape attribution on the
   * signal edge (validatedBy atlas:WealthSignalTypeShape …). Passed as a slot so
   * the shared card reuses each app's existing component without importing across
   * the app boundary.
   */
  signalProvenance?: React.ReactNode;
  /**
   * Framing. "wholesale" = the banker's read (the customer instantiates the
   * model); "wealth" = the advisor's-side read (advisesCustomer). Same shared
   * ontology classes either way — only the one-line framing differs.
   */
  perspective?: "wholesale" | "wealth";
}

/** A small atlas:Class → fibo:Class mapping row, rendered as the warm-paper chips. */
function GroundingRow({
  live,
  edge,
  atlasClass,
  fiboClass,
  note,
  children,
}: {
  /** The live instance presence for this customer (e.g. "2 accounts"), or null for the entity itself. */
  live?: string | null;
  /** The ontology edge that connects it to the customer (e.g. "hasAccount"). */
  edge?: string;
  /** The atlas: class this customer instantiates. */
  atlasClass: string;
  /** The FIBO superclass (subClassOf), or undefined for bank-specific classes with no FIBO counterpart. */
  fiboClass?: string;
  /** For bank-specific classes: the honest "no FIBO counterpart" note. */
  note?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="cov">
      <div className="cov-top">
        {edge && <span className="chip">atlas:{edge}</span>}
        <span className="cov-name">{atlasClass}</span>
        {fiboClass ? (
          <>
            <span className="chip" aria-label="subClassOf">
              ⊑ {fiboClass}
            </span>
          </>
        ) : (
          <span className="chip">{note}</span>
        )}
        {live && (
          <span className="cov-state on" style={{ marginLeft: "auto" }}>
            <span className="lab-live">live</span> {live}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

/**
 * Build the customer's INSTANCE neighborhood as a {nodes,edges} model from the data
 * already fetched. Center = the customer; neighbors = ONLY the node-types whose data
 * is present (the honest conditional — e.g. wealth doesn't fetch accounts, so no
 * account node is created; nothing is invented). All nodes/edges are kind "live" —
 * these are real per-customer fetched facts. Positions come from the deterministic
 * radial layout (center + ring), so the result is stable and screenshot-friendly.
 */
function buildInstanceGraph(args: {
  customerLabel: string;
  hasAccounts: boolean;
  accountCount?: number;
  hasHousehold: boolean;
  householdMemberCount?: number;
  hasSignals: boolean;
  signalCount?: number;
  hasAdvisory: boolean;
  advisorLabel?: string;
  perspective: "wholesale" | "wealth";
}): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const width = 560;
  const height = 360;
  const center = { id: "customer" };
  const neighbors: { id: string; label: string; sublabel?: string; edge: string }[] = [];

  if (args.hasAccounts) {
    const n = args.accountCount;
    neighbors.push({
      id: "account",
      label: "Account",
      sublabel: typeof n === "number" ? `${n} held` : undefined,
      edge: "hasAccount",
    });
  }
  if (args.hasHousehold) {
    const n = args.householdMemberCount;
    neighbors.push({
      id: "household",
      label: "Household",
      sublabel: typeof n === "number" ? `${n} member${n === 1 ? "" : "s"}` : undefined,
      edge: "memberOf",
    });
  }
  if (args.hasSignals) {
    const n = args.signalCount;
    neighbors.push({
      id: "signal",
      label: "WealthSignal",
      sublabel: typeof n === "number" ? `${n} derived` : undefined,
      edge: "producesSignal",
    });
  }
  if (args.hasAdvisory) {
    neighbors.push({
      id: "advisor",
      label: "Advisor",
      sublabel: args.advisorLabel,
      edge: args.perspective === "wealth" ? "advisesCustomer" : "coveringAdvisor",
    });
  }

  const { positions, anchors } = radialLayout(center, neighbors, { width, height });

  const nodes: GraphNode[] = [
    {
      id: "customer",
      label: args.customerLabel || "Customer",
      sublabel: "atlas:Customer",
      type: "instance",
      kind: "live",
      shape: "circle",
      x: positions.customer.x,
      y: positions.customer.y,
      // The hub labels below itself (clear of the radiating neighbor labels above/beside).
      labelAnchor: "below",
    },
    ...neighbors.map((nb) => ({
      id: nb.id,
      label: nb.label,
      sublabel: nb.sublabel,
      type: "instance" as const,
      kind: "live" as const,
      shape: "circle" as const,
      x: positions[nb.id].x,
      y: positions[nb.id].y,
      labelAnchor: anchors[nb.id],
    })),
  ];

  // The advisory edge points advisor→customer on the wealth side (advisesCustomer),
  // customer→advisor on the wholesale side (coveringAdvisor).
  const edges: GraphEdge[] = neighbors.map((nb) =>
    nb.id === "advisor" && args.perspective === "wealth"
      ? { from: "advisor", to: "customer", label: nb.edge, kind: "live" as const }
      : { from: "customer", to: nb.id, label: nb.edge, kind: "live" as const },
  );

  return { nodes, edges };
}

export function SemanticGroundingCard({
  customerLabel,
  hasAccounts = false,
  accountCount,
  hasHousehold = false,
  householdMemberCount,
  hasSignals = false,
  signalCount,
  hasAdvisory = false,
  advisorLabel,
  signalProvenance,
  perspective = "wholesale",
}: SemanticGroundingCardProps) {
  const framing =
    perspective === "wealth"
      ? "This client is grounded in the FIBO-aligned model — the advisor reads the same graph the banker wrote to:"
      : "This customer instantiates the FIBO-aligned model — every fact below is a real class and edge in the loaded ontology:";

  const instanceGraph = buildInstanceGraph({
    customerLabel: customerLabel || "Customer",
    hasAccounts,
    accountCount,
    hasHousehold,
    householdMemberCount,
    hasSignals,
    signalCount,
    hasAdvisory,
    advisorLabel,
    perspective,
  });

  return (
    <div className="card">
      <div className="card-h">
        <span className="t">Semantic grounding</span>
        {/* Kind-of-truth precision: the "live" pill attaches ONLY to the per-customer
            INSTANCE; "FIBO 2024 Q3" is the loaded-SCHEMA version provenance, not a
            live-queried claim. The two truths are labelled distinctly. */}
        <span className="meta">
          <span className="lab-live">live</span> instance · model FIBO 2024 Q3
        </span>
      </div>

      <p className="card-note">{framing}</p>

      {/* INSTANCE GRAPH — the customer's real fetched neighborhood as a node-link diagram
          (the visual hero), sitting ABOVE the precise FIBO-grounding rows below. LIVE visual
          treatment (solid, green): every node/edge is a per-customer fetched fact, so the
          "live · this customer" caption is truthful. Only the present node-types are drawn —
          nothing invented. Rendered only when the customer has at least one neighbor (a lone
          center node is not a graph). */}
      {instanceGraph.nodes.length > 1 && (
        <div className="nlg-wrap" style={{ marginBottom: 12 }}>
          <div className="card-h" style={{ marginBottom: 6 }}>
            <span className="meta" style={{ marginLeft: 0 }}>
              <span className="lab-live">live</span> this customer · fetched neighborhood
            </span>
          </div>
          <NodeLinkGraph
            nodes={instanceGraph.nodes}
            edges={instanceGraph.edges}
            width={560}
            height={360}
            ariaLabel={`${customerLabel || "Customer"} — fetched graph neighborhood`}
          />
          <p className="card-note" style={{ marginTop: 4, fontSize: 10.5 }}>
            Drag any node to explore · the layout resets on reload.
          </p>
        </div>
      )}

      {/* (a) FIBO grounding — the atlas→FIBO alignment this customer instantiates.
          The entity itself is always shown; the related classes appear only when
          that data is present for the customer (conditional, like the other cards). */}
      <GroundingRow
        atlasClass="atlas:Customer"
        fiboClass="fibo:IndependentParty"
        live="this entity"
      />

      {hasAccounts && (
        <GroundingRow
          edge="hasAccount"
          atlasClass="atlas:Account"
          fiboClass="fibo:FinancialAccount"
          live={
            typeof accountCount === "number"
              ? `${accountCount} account${accountCount === 1 ? "" : "s"}`
              : "held"
          }
        />
      )}

      {hasHousehold && (
        <GroundingRow
          edge="memberOf"
          atlasClass="atlas:Household"
          note="bank-specific · no FIBO counterpart"
          live={
            typeof householdMemberCount === "number"
              ? `${householdMemberCount} member${householdMemberCount === 1 ? "" : "s"}`
              : "member"
          }
        />
      )}

      {hasSignals && (
        <GroundingRow
          edge="producesSignal"
          atlasClass="atlas:WealthSignal"
          note="bank-specific · SHACL-derived"
          live={
            typeof signalCount === "number"
              ? `${signalCount} signal${signalCount === 1 ? "" : "s"}`
              : "derived"
          }
        >
          {/* SHACL-shape attribution — each app passes its own <ProvenanceBadge>
              (validatedBy atlas:WealthSignalTypeShape · derivedFrom … · generatedBy …). */}
          {signalProvenance}
        </GroundingRow>
      )}

      {hasAdvisory && (
        <GroundingRow
          edge={perspective === "wealth" ? "advisesCustomer" : "coveringAdvisor"}
          atlasClass="atlas:Advisor"
          fiboClass="fibo:FunctionalRole"
          live={advisorLabel || "covered"}
        />
      )}

      {/* The loaded-schema caption — makes the second truth explicit so the card
          does not overclaim its own alignment as live-queried. */}
      <p className="card-note" style={{ marginTop: 10 }}>
        The atlas → FIBO <code>rdfs:subClassOf</code> alignment above is the loaded ontology
        schema (FIBO 2024 Q3 Production Release) — the same for every customer, not queried
        live per customer. The <span className="lab-live">live</span> pill marks only the
        per-customer instance data fetched from the graph.
      </p>

      {/* (b) Lineage strip — the REAL ATLAS source path LIVE/unshaded, then the
          external systems-of-record SHADED as "possible next" (not bound). */}
      <div className="cov" style={{ marginTop: 12 }}>
        <div className="cov-top">
          <span className="cov-name">Lineage</span>
          <span className="meta" style={{ marginLeft: "auto" }}>
            <span className="lab-live">live</span> real ATLAS path
          </span>
        </div>
        <p className="prov" aria-label="ATLAS source path (live)">
          <span aria-hidden="true" className="gem">
            ◈
          </span>
          <span>
            <b>data load</b> → <b>LGD</b> → <b>Entity Resolution</b> → <b>SLGD</b> →{" "}
            <b>WealthSignals</b> (SHACL-validated)
          </span>
        </p>
      </div>

      <div className="future-band">
        <div className="future-h">
          <svg
            className="i"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--future)"
            strokeWidth="1.7"
          >
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
          <span className="lab">Possible next — external systems of record</span>
          <span className="note">roadmap — not shown as live</span>
        </div>
        <p className="future-body">
          The same FIBO-aligned model can bind to the bank&apos;s systems of record —{" "}
          <b>CIF</b>, <b>nCino</b>, <b>Snowflake</b> — as federated sources. Shown shaded
          because they are <b>not bound</b> in this demo: the live path above is the real
          ATLAS lineage; these are the target, not yet wired.
        </p>
      </div>
    </div>
  );
}
