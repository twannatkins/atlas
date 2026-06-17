---
title: "Module 5 — GraphQL Federation: The FIBO-Shaped API"
weight: 50
---

# Module 5 — GraphQL Federation: The FIBO-Shaped API

## Learning Objectives

- Explain why ATLAS's GraphQL schema is called "FIBO-shaped" and what that means
  for the contract between Workshop 1 and Workshop 2
- Trace the two resolver paths the running system actually uses: a **read path**
  that queries Neptune directly (SigV4, in-VPC, no agent) and an **action path**
  that invokes an AgentCore agent (`askGraph`, `draftRationale`, `converse`) or a
  Step Function (`routeReferral`)
- Implement and verify both paths using the schema from
  `spec/05-appsync-graphql/schema.graphql`
- Be precise about the persona claim: it gates *which fields a caller may invoke*
  (access control, enforced today), not *which rows come back* (per-row Lake
  Formation scoping is roadmap, not enforced)

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 4 — Agent Registry](../04-agent-registry/) complete
- The five Phase 1 agents registered and discovery verified

## What You Will Build

Simulated implementations of the two GraphQL resolver paths, verified against the
AppSync schema: a **read path** (direct Neptune SPARQL — the resolver runs the
query against Neptune itself, no MCP, no agent) and an **action path** (the
resolver invokes an AgentCore agent for `askGraph` / `draftRationale` / `converse`,
or a Step Function for `routeReferral`). You will also see, honestly, what the
persona claim does today: it gates field/capability *access*, not which rows a
query returns.

The notebook is `notebooks/phase-1-referral/04_graphql_federation.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`). The Key Terms table defines "resolver pattern," "Ontop," and
"canonical URI" as used in the schema and throughout Phase 2.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/04_graphql_federation.ipynb` in SageMaker
Studio. Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why every GraphQL type carries a docstring that names its FIBO ontology class
- Why the schema is the contract that makes Workshop 1's ontology visible to
  the Workshop 2 UIs
- The two paths behind the schema (direct-Neptune reads vs. agent actions), and
  the honest permission model: the persona claim gates *which fields a caller may
  invoke* (enforced), while per-row Lake Formation scoping is roadmap, not enforced

### Step 3 — Run setup and load the schema (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and read the GraphQL schema
from `spec/05-appsync-graphql/schema.graphql`.

Expected output:

```
Shared helpers loaded.
Schema loaded: N characters
Types found: Customer, Advisor, WealthSignal, RoutingDecision, AuditRecord, ...
```

### Step 4 — Inspect the ontology mapping (cell 4)

Run cell 4 (`cell-04-inspect-schema`) to extract the docstring-to-type mapping
from the schema — the machine-readable record of which FIBO class each GraphQL
type represents.

Expected output:

```
Ontology mapping from schema docstrings:
  Customer         → atlas:Customer
  Advisor          → atlas:Advisor
  WealthSignal     → atlas:WealthSignal
  RoutingDecision  → atlas:RoutingDecision
  AuditRecord      → atlas:AuditRecord
  ...
All entity types mapped to ontology classes.
```

### Step 5 — Simulate the read-path resolver (cell 5)

Run cell 5 (`cell-05-simulate-resolver`) to implement and run the **read path**:
the resolver translates a GraphQL `customer` query into SPARQL and runs it
**directly against Neptune** (SigV4-signed, in-VPC) — no MCP server, no agent in
the loop. This is the fast path the running system uses for every data read.

Expected output:

```
Read path: resolver → Neptune SLGD directly (SigV4, in-VPC)
  SPARQL (first 100 chars): ...
  Result: {uri: "atlas:cust/...", customerId: "CUST-9C2A1E", label: "..."}
```

### Step 6 — Run both real paths (cell 6)

Run cell 6 (`cell-06-three-patterns`) to implement and run both paths the running
system actually uses:
- **Read path** — direct Neptune SPARQL (no agent): `customer`, `wealthSignals`,
  `advisoryRelationships`, `referrals`, `auditTrail`
- **Action path** — resolver → AgentCore agent: `askGraph` → nl-to-sparql-agent
  (and `draftRationale` / `converse`); `routeReferral` starts a Step Function

Expected output:

```
1. Read — graph data (direct Neptune, no agent): Signals found: 2
2. Action — natural-language query (resolver → nl-to-sparql-agent):
   status=success template=signals_for_customer rows=2
```

![Both resolver paths output](/static/images/05-step-06-three-patterns.png)

The action path is **template-bounded**: `nl-to-sparql-agent` never free-generates
SPARQL — it matches the question to one of a fixed, validated set and runs that. Hold
onto this property: because the query that runs is one of a *known* set, the part of the
ontology it traverses is knowable in advance. That is exactly what lets the Wholesale and
Wealth UIs honestly **highlight the schema graph** when you ask a question — the model
lights up to show the path a real query took. The payoff is taught in
[Module 6 — Wholesale UI](../06-wholesale-ui/); this template-bounded design is what makes
it trustworthy rather than decorative.

### Step 7 — What the persona claim does today (cell 7)

Run cell 7 (`cell-07-persona-scoping`). It is honest about access control: the
persona claim gates *which fields/capabilities a caller may invoke* (for example,
only `atlas-consumer-banker` may call `draftRationale`). It does **not** return a
different set of rows per persona — per-row Lake Formation scoping is roadmap, not
enforced; the direct-Neptune read path returns the same rows regardless of caller.

Expected output:

```
Access control — who may call draftRationale (enforced today):
  atlas-consumer-banker    → ALLOWED
  atlas-wealth-advisor     → REFUSED
  atlas-bsa-analyst        → REFUSED
(A refused persona is denied the CALL — not handed a smaller row set.)
```

### Step 8 — Verify schema mapping (cell 9)

Run cell 9 (`cell-09-verify-schema-mapping`) to assert that every non-infrastructure
entity type in the schema has a docstring that names an `atlas:` or `atlas-part-2:`
ontology class.

Expected output:

```
Schema mapping verification
  Customer:        atlas:Customer  ✓
  Advisor:         atlas:Advisor   ✓
  WealthSignal:    atlas:WealthSignal  ✓
  ...
[PASS] All entity types mapped to ontology classes.
```

### Step 9 — Verify resolver shapes (cell 10)

Run cell 10 (`cell-10-verify-resolver-shapes`) to confirm that each resolver
pattern returns the fields declared in the schema.

### Step 10 — Verify access control assertion (cell 11)

Run cell 11 (`cell-11-verify-persona-scoping`) to assert the *access-control*
layer: only allow-listed personas may invoke a protected field (e.g. only the
Consumer Banker may `draftRationale` or `routeReferral`). It deliberately does
**not** assert a different row count per persona — that would test a fiction,
because row scoping is roadmap.

Expected output:

```
✓ Access control confirmed: the persona claim decides WHO MAY CALL each field.
  Per-row data scoping is roadmap — the read path returns the same rows for all personas.
```

## Expected Outputs

- Both resolver paths (read = direct Neptune, action = agent) return correctly shaped responses
- Schema mapping verification prints `[PASS] All entity types mapped to ontology classes`
- Access-control assertion confirms only allow-listed personas may invoke a protected field

## Troubleshooting

**Cell 3 fails: "schema.graphql not found"**

The schema file is at `use-case-applications/spec/05-appsync-graphql/schema.graphql`.
The notebook resolves it relative to `notebooks/phase-1-referral/`. Print
`SCHEMA_PATH` in cell 3 to confirm the absolute path and verify the file exists.

**Cell 4 reports "0 types mapped"**

The regex in cell 4 matches the pattern `"""\n<ontology-class>\n"""\ntype <Name>`.
If the schema docstrings use a different format (inline `"""class"""`, or no
newlines), the regex will not match. Open the schema file and confirm the
docstring format matches the expected pattern.

**Cell 7 — expecting different row counts per persona?**

That is the most common misconception, so the cell is written to prevent it. The
persona claim controls *which fields/capabilities a caller may invoke* (access
control), not which rows a query returns. Per-row Lake Formation scoping — the
same query returning different rows per persona — is **roadmap, not enforced**;
the direct-Neptune read path returns the same rows regardless of caller. If you
expected a row-count delta, re-read cell 2's "what the persona claim does — and
does not — do today" section.

**Cell 9 fails: "type Capability has no ontology mapping"**

`Capability` is an infrastructure type (it represents the registry response, not
an ontology entity). The verification cell excludes `{"Query", "Mutation",
"Subscription", "Provenance", "Capability"}` from the mapping check. If the check
still fails on `Capability`, verify the exclusion set in the cell source.

## What's Next

The data driver (GraphQL/AppSync) and the capability driver (Agent Registry) are
both working. [Module 6 — Wholesale UI](../06-wholesale-ui/) wires them together
into the two-driver architecture — and demonstrates the compliance constraint that
governs the entire Phase 1 UI surface: the tipping-off prohibition under
31 U.S.C. §5318(g)(2).
