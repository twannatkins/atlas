# ATLAS — Follow-on Labs

The workshop builds a complete reference implementation of the three-layer
architecture on a synthetic dataset. This document describes two extension paths
that take the architecture further. Neither is a turnkey lab with a notebook you
run end to end — each is a **design sketch** that shows where the workshop stops
short, what the extension adds, and how to build it against the architecture you
already have. They are starting points for your own engineering, not pre-built
content.

Both labs preserve the central commitment of ATLAS: the deterministic-vs-probabilistic
boundary. Anything you add must still cross that boundary through the same two
mechanisms the workshop built — the SHACL shapes (Module 6) and the
`atlas_sparql.validate()` pre-check (Module 7).

## Before you start

- Complete Modules 1–8 at least once so the SLGD holds promoted data and the
  ontology is loaded.
- Have the Neptune infrastructure deployed, or be ready to redeploy it from the
  Module 3 CloudFormation stack.
- Be comfortable with the Module 4 connection patterns, especially Pattern C
  (the Lambda event path), since both labs build on it.

---

## Lab 1 — Real-Time Signal Detection

*(the real-time depth lab)*

### Where the workshop stops short

Module 4 introduces three connection patterns. Pattern C is the real-time path:
an AWS Lambda function receives a wealth-eligibility event and writes triples to
Neptune. In the workshop, Pattern C is demonstrated as a **replay** — cell 8 takes
one synthetic event and shows how it converts to N-Triples. No live event stream
is wired. The signals that drive Module 8 are derived in batch by the Module 5
SPARQL CONSTRUCT queries, not produced in real time.

That is the right scope for teaching the pattern. It leaves the live path as an
exercise.

### What this lab adds

A live ingestion path: a stream of transaction or account events flows into the
LGD as they occur, the promotion path lifts qualifying events into the SLGD, and
the SHACL validator runs on the streaming write path so that nothing crosses the
boundary unvalidated.

### Architecture

```
Transaction system
       |
       v
Amazon Kinesis Data Streams  (one stream per event type)
       |
       v
AWS Lambda (R2RML mapper — same logic as Module 4 Pattern C mappings/lambda/)
       |
       v (SPARQL INSERT with PROV-O attribution)
Neptune LGD
       |
       v (promotion trigger — Lambda or Step Functions rule)
Promotion path (Module 5 logic)
       |  SHACL pre-check via atlas_sparql.validate() before each write
       v
Neptune SLGD
       |
       v
Existing Module 8 agent picks up new signals on next poll
```

### Key design decisions for this extension

**Event schema.** The Lambda in `mappings/lambda/` already converts a single
JSON event to N-Triples using a fixed schema. For live ingestion you need to pin
that schema version and handle schema evolution (add a version field to events and
route old/new formats through separate mapping functions).

**Promotion trigger.** The workshop runs promotion manually (Module 5 cells). In
live ingestion, promotion can be triggered by a Lambda that polls the LGD for
unprocessed events on a schedule, or by an EventBridge rule that fires when the
LGD receives a new triple in the transaction graph. The rule-based trigger avoids
polling latency but requires Neptune Streams (available on Neptune 1.2+).

**SHACL on the write path.** `atlas_sparql.validate()` already rejects writes
that violate the boundary. Add it to the promotion Lambda so every INSERT is
validated before it reaches the SLGD. The cost is negligible for event-sized
payloads (one triple set per transaction); it becomes meaningful for bulk loads,
which should stay on the S3 bulk-load path from Module 3.

**Idempotency.** Neptune does not deduplicate triple insertions. If the Lambda
retries on failure, it may insert duplicate triples. Use a deterministic URI
scheme for event instances (hash of source-system transaction ID) so that retried
inserts are no-ops against an already-loaded event.

### Expected outcome

After this lab, a single deposit transaction flowing through Kinesis produces a
`LargeDepositPattern` signal in the SLGD within the Lambda invocation window
(typically under 1 second). The Module 8 agent requires no changes — it queries
the SLGD for signals and will pick up the new signal on its next run.

---

## Lab 2 — External Signals

*(the external-signals lab)*

### Where the workshop stops short

ATLAS v1.0 sources all wealth signals from **inside the bank**: deposit
transactions, account balances, household aggregations, advisor assignments, and
referral history. This is architecturally deliberate — the workshop establishes
the pattern on data every institution already has before introducing the
complexity of external data governance.

The `atlas-core.ttl` ontology comment is explicit: "Wealth signals in v1 are
sourced from inside the bank only. External signals are an extension path
documented in Section 7."

### What this lab adds

Three external signal types, each sourced from a public or licensed registry:

| Signal Type | Source | Rule |
|-------------|--------|------|
| `PropertyTransactionSignal` | County property deed registry (public record) | Customer's name appears as buyer on a deed recorded ≥ $750,000 in the last 180 days |
| `LEIOwnershipChangeSignal` | GLEIF LEI registry (public) | A Legal Entity Identifier linked to the customer's employer changes ownership structure (new parent, acquisition) |
| `RegulatoryFilingSignal` | SEC EDGAR (public) | A form 4 or 13-F filing associates the customer's name with material equity holdings |

These signal types require new SKOS concepts in `ontology/atlas-core.ttl` (the
v1.0 `WealthSignalType` concept scheme covers `LargeDepositPattern` and
`HouseholdAggregationSignal`; each new external type is a new narrower concept),
a new Pattern D connection (scheduled ingestion from the external source), and
new SPARQL CONSTRUCT rules in the Module 5 style.

### Architecture

```
External registry (property, GLEIF, EDGAR)
       |
       v (scheduled pull — AWS Lambda or Glue job, daily or weekly)
S3 staging bucket (same bucket as Module 3)
       |
       v (R2RML mapping — new mapping file per source type)
Neptune LGD (separate named graph per external source for lineage isolation)
       |
       v (promotion — same path as Module 5)
Neptune SLGD
       |
       v
Module 8 agent (no changes required)
```

### Key design decisions for this extension

**Identity resolution.** Internal signals match customers by internal account ID.
External signals match customers by name, address, or employer — fuzzy matches
that require entity resolution. Use AWS Entity Resolution (already in the
architecture from Module 5) to link external records to `atlas:Customer` URIs
before loading into the LGD. Do not load unresolved records — an unresolved
external signal is noise, not evidence.

**Provenance per source.** ATLAS uses PROV-O to track where every triple comes
from. External sources need their own `prov:Agent` nodes (e.g.,
`atlas:GLEIFRegistry`, `atlas:SECEdgar`) and a `prov:wasAttributedTo` link on
every triple they contribute. This is the same pattern as the
`atlas:LegacyDataMigration` provenance stamp in `extensions/prov-o-bindings.ttl`,
extended for each new source.

**Consent and data governance.** Property records and EDGAR filings are public,
but your institution's legal and compliance teams must sign off on ingesting them
into a customer graph. The architecture supports the governance — the provenance
trail, SHACL validation, and PROV-O attribution are all in place — but the
institutional policy decision precedes the engineering.

**SHACL extensions.** Each external signal type needs a new SKOS concept in the
`WealthSignalType` concept scheme and a corresponding SHACL shape that verifies
the signal instance carries the required provenance fields. Add these to
`ontology/atlas-shapes.ttl` before loading data. The existing `WealthSignalTypeShape`
(Shape 5 in Module 6) becomes the template.

### Expected outcome

After this lab, the Module 5 SPARQL CONSTRUCT queries run against a richer LGD
that includes external observations. The Module 8 agent surfaces signals from
all three new types alongside the existing `LargeDepositPattern` and
`HouseholdAggregationSignal` signals. The CIO demo query from Module 8 cell 14
returns results from both internal and external evidence paths, with full
provenance distinguishing the two.

---

## How the labs relate to the workshop

| Workshop artifact | Used in | Extended by |
|-------------------|---------|-------------|
| `mappings/lambda/` R2RML mapper | Module 4 Pattern C demo | Lab 1 (live Kinesis trigger) |
| Module 5 promotion path | Batch promotion | Lab 1 (streaming trigger), Lab 2 (new signal types) |
| `atlas_sparql.validate()` pre-check | Module 7 NL-to-SPARQL boundary | Lab 1 (write-path validation on promotion Lambda) |
| `ontology/atlas-shapes.ttl` SHACL shapes | Module 6 validation gate | Lab 2 (new WealthSignalType shapes) |
| AWS Entity Resolution (Module 5) | Internal identity resolution | Lab 2 (external record matching) |
| `extensions/prov-o-bindings.ttl` | Governance extensions | Lab 2 (new prov:Agent per external source) |

Neither lab requires changes to Modules 1–3, 6, or 7. The ontology and the
boundary mechanisms are stable; the extension points are in the data integration
layer (Modules 4–5) and the signal taxonomy.
