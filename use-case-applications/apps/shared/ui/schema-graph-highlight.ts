/**
 * Schema-graph highlight derivation — Increment 2 (honest, question-driven).
 *
 * Turns a REAL askGraph answer into highlight + selective-count state for the schema
 * graph. Every value here is derived from what the live, template-bounded
 * nl-to-sparql-agent ACTUALLY returned — never fabricated.
 *
 * THE HONESTY BAR enforced in code:
 *  - The agent is template-bounded: it returns one of 10 fixed templates' real SPARQL,
 *    tagged with `templateId` (= the template's `note` string). The CURATED_MAP below is
 *    keyed by those exact note strings — the only derivation source. Cross-checked against
 *    the returned `sparql` (every entry lists `expectTokens` that MUST appear) so a drifted
 *    note or an unexpected query falls to the no-map path instead of highlighting wrongly.
 *  - Counts are taken ONLY where the real result shape carries them honestly:
 *      · groupby  — template 3's real GROUP BY rows (per-signal-type counts) → WealthSignal.
 *      · rowtotal — a result-row count on the primary queried node, LABELLED "results"
 *                   (a count of answer rows, NOT a graph cardinality).
 *      · none     — join-row templates (T2) and anything not in the map: NO count.
 *  - status != success, an unmapped templateId, or a guard mismatch → active:false (no
 *    highlight; the schema graph stays in its neutral resting state) + an honest message.
 *
 * The schema graph itself stays the LOADED-SCHEMA view (neutral, "model FIBO 2024 Q3", no
 * live pill). The highlight is a query-response OVERLAY on the loaded model — it shows which
 * part a real query traversed; it does NOT reclassify the schema as live-per-customer.
 */

export interface NlQueryResultLike {
  status?: string | null;
  sparql?: string | null;
  result?: unknown; // AWSJSON — array, or JSON string of an array
  templateId?: string | null;
}

type CountKind = "groupby" | "rowtotal" | "none";

interface MapEntry {
  /** Schema node ids to highlight (the rest are dimmed when active). */
  nodes: string[];
  /** Unordered node-id pairs whose edge should highlight, e.g. ["Customer", "Account"]. */
  edges: [string, string][];
  /**
   * atlas: tokens that MUST appear in the returned SPARQL. Two honest roles:
   *  - the GUARD for the templateId path (wholesale askGraph): the returned SPARQL must
   *    carry these or we fall to no-map (catches a drifted note).
   *  - the REQUIRE set for the SPARQL-signature path (wealth converse, which returns no
   *    templateId): an entry matches only if ALL expectTokens are present.
   */
  expectTokens: string[];
  /**
   * Tokens that must be ABSENT for the SPARQL-signature match to pick this entry — they
   * disambiguate templates that share tokens (e.g. T1 vs T2: T1 forbids evidencedBy so
   * T2's superset SPARQL can't false-match T1). Derived from the real template structure.
   */
  forbidTokens?: string[];
  /** How (and whether) to annotate a count, and on which node. */
  countKind: CountKind;
  countNode?: string;
}

/**
 * The curated map — keyed by the agent's templateId (the template `note` string from
 * ground-truth.yaml). Built from the read's verified traversal table. T9/T10 are
 * deliberately ABSENT (they traverse RoutingDecision, which is not a node on the 5-type
 * schema graph, and are empty until a referral is routed) → they fall to the no-map path.
 */
export const CURATED_MAP: Record<string, MapEntry> = {
  "Story 1 — find the opportunity": {
    nodes: ["Customer", "WealthSignal"],
    edges: [["Customer", "WealthSignal"]],
    expectTokens: ["atlas:producesSignal", "atlas:hasSignalType"],
    forbidTokens: ["atlas:evidencedBy"], // disambiguate from T2 (which adds evidencedBy)
    countKind: "rowtotal",
    countNode: "Customer",
  },
  "Story 2 — the evidence behind the signal": {
    // Joins Customer × WealthSignal × Transaction rows — NO honest per-node count.
    // Transaction is NOT a node on this graph; do not invent one.
    nodes: ["Customer", "WealthSignal"],
    edges: [["Customer", "WealthSignal"]],
    expectTokens: ["atlas:evidencedBy", "atlas:producesSignal"],
    countKind: "none",
  },
  "Story 3 — size the opportunity by signal type": {
    nodes: ["WealthSignal"],
    edges: [],
    expectTokens: ["atlas:WealthSignal", "atlas:hasSignalType"],
    countKind: "groupby",
    countNode: "WealthSignal",
  },
  "Story 4 — who is actionable (uncovered)": {
    nodes: ["Customer", "Account", "Advisor"],
    edges: [
      ["Customer", "Account"],
      ["Customer", "Advisor"],
    ],
    expectTokens: ["atlas:hasAccount", "atlas:hasAdvisor"],
    countKind: "rowtotal",
    countNode: "Customer",
  },
  "Story 5 — household-level opportunity": {
    nodes: ["Customer", "Household", "Advisor"],
    edges: [
      ["Customer", "Household"],
      ["Customer", "Advisor"],
    ],
    expectTokens: ["atlas:memberOf", "atlas:hasAdvisor"],
    countKind: "rowtotal",
    countNode: "Household",
  },
  "Story 6 — map the household": {
    nodes: ["Customer", "Household"],
    edges: [["Customer", "Household"]],
    expectTokens: ["atlas:memberOf"],
    // disambiguate from T5 (memberOf + hasAdvisor); T6 is the plain household map.
    forbidTokens: ["atlas:hasAdvisor"],
    countKind: "rowtotal",
    countNode: "Household",
  },
  "Story 7 — the financial picture": {
    nodes: ["Customer", "Account"],
    edges: [["Customer", "Account"]],
    expectTokens: ["atlas:hasAccount"],
    // disambiguate from T4 (hasAccount + hasAdvisor); T7 is the plain accounts query.
    forbidTokens: ["atlas:hasAdvisor"],
    countKind: "rowtotal",
    countNode: "Account",
  },
  "Story 8 — coverage history (temporal)": {
    nodes: ["Customer", "Advisor"],
    edges: [["Customer", "Advisor"]],
    expectTokens: ["atlas:coveringAdvisor"],
    countKind: "rowtotal",
    countNode: "Advisor",
  },
};

/** Parse the AWSJSON result into a row array (string → JSON, or already-array). */
export function parseRows(result: unknown): Record<string, unknown>[] {
  if (Array.isArray(result)) return result as Record<string, unknown>[];
  if (typeof result === "string") {
    try {
      const p = JSON.parse(result);
      return Array.isArray(p) ? p : [];
    } catch {
      return [];
    }
  }
  return [];
}

/** Canonical unordered edge key. */
export function edgeKey(a: string, b: string): string {
  return [a, b].sort().join("|");
}

export interface SchemaHighlightState {
  /** True only when a real, mapped, guard-passing answer drives the overlay. */
  active: boolean;
  /** Node ids to highlight (others dim when active). */
  nodeIds: string[];
  /** Highlighted edges as canonical keys (edgeKey). */
  edgeKeys: string[];
  /** nodeId → honest count badge text (only where the result shape carries it). */
  badges: Record<string, string>;
  /** An honest note to show when a real answer doesn't map to the model view (else null). */
  message: string | null;
}

const RESTING: SchemaHighlightState = {
  active: false,
  nodeIds: [],
  edgeKeys: [],
  badges: {},
  message: null,
};

/**
 * Derive the schema-graph overlay state from a REAL askGraph result. Pure + deterministic
 * against the fixed templates — this is the machine-verifiable core (the LIVE
 * ask→agent→Neptune→rows round-trip is browser-confirmed).
 */
export function deriveSchemaHighlight(res: NlQueryResultLike | null | undefined): SchemaHighlightState {
  if (!res) return RESTING; // nothing asked yet → resting graph
  const status = res.status ?? "";

  // Non-success: the graph rests. no_template_match has its own honest note in the panel,
  // so we don't double up; execution_error likewise. No highlight, ever.
  if (status !== "success") return RESTING;

  const templateId = (res.templateId ?? "").trim();
  const entry = templateId ? CURATED_MAP[templateId] : undefined;

  // A real success whose template isn't in the curated map (e.g. T9/T10 routing/audit —
  // RoutingDecision is not on this 5-type graph): honest note, NO arbitrary highlight.
  if (!entry) {
    return { ...RESTING, message: "This answer doesn’t map to the model view." };
  }

  // GUARD: the returned SPARQL must contain the expected atlas: tokens for this template.
  // If a note drifted onto the wrong query, this fails → no-map path (fail-safe, no false
  // highlight).
  const sparql = res.sparql ?? "";
  const guardOk = entry.expectTokens.every((tok) => sparql.includes(tok));
  if (!guardOk) {
    return { ...RESTING, message: "This answer doesn’t map to the model view." };
  }

  return buildState(entry, res.result);
}

/** Build the overlay state from a matched entry + the real result rows. */
function buildState(entry: MapEntry, result: unknown): SchemaHighlightState {
  const rows = parseRows(result);
  const badges: Record<string, string> = {};

  if (entry.countKind === "rowtotal" && entry.countNode) {
    const n = rows.length;
    badges[entry.countNode] = `${n} result${n === 1 ? "" : "s"}`;
  } else if (entry.countKind === "groupby" && entry.countNode) {
    const types = rows.length;
    let total = 0;
    for (const r of rows) {
      const c = Number((r as Record<string, unknown>).count ?? (r as Record<string, unknown>)["?count"] ?? 0);
      if (!Number.isNaN(c)) total += c;
    }
    badges[entry.countNode] =
      total > 0 ? `${types} type${types === 1 ? "" : "s"} · ${total} signals` : `${types} type${types === 1 ? "" : "s"}`;
  }

  return {
    active: true,
    nodeIds: entry.nodes,
    edgeKeys: entry.edges.map(([a, b]) => edgeKey(a, b)),
    badges,
    message: null,
  };
}

/**
 * Match a returned SPARQL to a curated entry by its atlas: token signature — for the WEALTH
 * `converse` path, which returns `sparql` + `result` but NO templateId. An entry matches
 * only when ALL its expectTokens are present AND none of its forbidTokens are; the match
 * must be UNIQUE (exactly one entry) or we return null (→ no-map). This is honest: it
 * recognises the real query that ran by its real structure, and refuses to guess when
 * ambiguous. Deterministic against the fixed templates.
 */
export function matchEntryBySparql(sparql: string): MapEntry | null {
  if (!sparql) return null;
  const hits = Object.values(CURATED_MAP).filter((entry) => {
    const hasAll = entry.expectTokens.every((t) => sparql.includes(t));
    const hasForbidden = (entry.forbidTokens ?? []).some((t) => sparql.includes(t));
    return hasAll && !hasForbidden;
  });
  return hits.length === 1 ? hits[0] : null; // unique match only — never guess
}

/**
 * Wealth-side derivation (converse → ConverseResult: status, sparql, result, NO templateId).
 * Recognises the query by its SPARQL signature; everything else (status gate, no-map note,
 * honest counts) is identical to the wholesale path. Real answers only; never fabricated.
 */
export function deriveSchemaHighlightFromConverse(
  res: { status?: string | null; sparql?: string | null; result?: unknown } | null | undefined,
): SchemaHighlightState {
  if (!res) return RESTING;
  if ((res.status ?? "") !== "success") return RESTING;
  const entry = matchEntryBySparql(res.sparql ?? "");
  if (!entry) return { ...RESTING, message: "This answer doesn’t map to the model view." };
  return buildState(entry, res.result);
}
