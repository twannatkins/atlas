---
title: "Module 5 — GraphQL Federation: The FIBO-Shaped API"
weight: 50
---

# Module 5 — GraphQL Federation: The FIBO-Shaped API

## Learning Objectives

- Explain why ATLAS's GraphQL schema is called "FIBO-shaped" and what that means
  for the contract between Workshop 1 and Workshop 2
- Trace the three resolver patterns: SPARQL via Ontop (Iceberg data), direct
  Neptune SPARQL (graph-native data), and Entity Resolution (source ID → canonical URI)
- Implement and verify all three patterns using the schema from
  `spec/05-appsync-graphql/schema.graphql`
- Confirm that persona scoping is passed through the resolver layer, not enforced
  there — and explain why that separation of concerns matters

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 4 — Agent Registry](../04-agent-registry/) complete
- The five Phase 1 agents registered and discovery verified

## What You Will Build

Simulated implementations of all three GraphQL resolver patterns, verified against
the AppSync schema. Each resolver accepts a persona claim and passes it through to
the MCP layer — it does not re-enforce permissions itself.

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
- Why AppSync, not the agents, is the right place for persona-scoped data access

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

### Step 5 — Simulate the Ontop resolver (cell 5)

Run cell 5 (`cell-05-simulate-resolver`) to implement and run Pattern 1: the
Ontop resolver that handles entity data stored in Iceberg tables. This resolver
translates a GraphQL `customer` query into a SPARQL query and sends it to the
Ontop endpoint.

Expected output:

```
Pattern 1 — Ontop resolver (Iceberg data)
  Query: customer(customerId: "CUST-001") { uri, label, customerId }
  → SPARQL generated
  → Ontop endpoint called
  → rows: 1
  Response: {uri: "atlas:cust/...", label: "...", customerId: "CUST-001"}
```

### Step 6 — Run all three resolver patterns (cell 6)

Run cell 6 (`cell-06-three-patterns`) to implement and run all three patterns
in sequence:
- **Pattern 1**: Ontop (Iceberg) — entity data
- **Pattern 2**: Direct Neptune SPARQL — graph-native data (WealthSignal, RoutingDecision, AuditRecord)
- **Pattern 3**: Entity Resolution — source ID to canonical URI lookup

Expected output:

```
Pattern 1 (Ontop):              rows=1  ✓
Pattern 2 (Direct Neptune):     rows=N  ✓
Pattern 3 (Entity Resolution):  canonical_uri=atlas:cust/...  ✓
```

![Three resolver patterns output](/static/images/05-step-06-three-patterns.png)

### Step 7 — Verify persona scoping (cell 7)

Run cell 7 (`cell-07-persona-scoping`) to confirm that the same GraphQL query
with different persona claims returns different row counts. The resolver does not
enforce the difference — it passes the claim to the MCP layer and the MCP layer
applies the Lake Formation scope.

Expected output:

```
Persona scoping check
  Consumer Banker   → rows: N (book-of-clients filtered)
  Wealth Advisor    → rows: M (different book)
  BSA Analyst       → rows: K (broader access)
  N ≠ M or K  ✓  (persona scoping works)
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

### Step 10 — Verify persona scoping assertion (cell 11)

Run cell 11 (`cell-11-verify-persona-scoping`) to assert that Consumer Banker
and BSA Analyst receive different row counts from the same query.

Expected output:

```
[PASS] Persona scoping: Consumer Banker ≠ BSA Analyst row counts.
```

## Expected Outputs

- All three resolver patterns return correctly shaped responses
- Schema mapping verification prints `[PASS] All entity types mapped to ontology classes`
- Persona scoping assertion prints `[PASS]`

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

**Cell 7 returns identical row counts for all personas**

The persona-scoping delta depends on Lake Formation row filtering being active.
If all personas see the same rows, the most likely cause is that the test
environment is not running inside the VPC, so the Lake Formation tags are not
being applied. Run from SageMaker Studio (inside the VPC) for row-filtered results.

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
