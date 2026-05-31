---
title: "Module 5 — Entity Resolution and the Promotion Path"
weight: 50
---

# Module 5 — Entity Resolution and the Promotion Path

## Learning Objectives

- Explain what entity resolution is and why it matters for cross-source knowledge graphs
- Configure rule-based and ML-based matching strategies and understand when to use each
- Write a promotion script that moves resolved entities from the LGD to the SLGD
  with full PROV-O (W3C Provenance Ontology) attribution
- Derive WealthSignal instances from promoted data using SPARQL CONSTRUCT queries
- Explain why promotion is a governed, discrete action — not an automatic pipeline

## Time Estimate

30 to 45 minutes.

## Prerequisites

- Module 4 complete (LGD populated with data from all three patterns)
- CloudFormation stack `atlas-neptune-twotier` running

## What You Will Build

This module produces:

- A populated SLGD (Semantic Layer Graph Database) with resolved customer entities,
  each carrying PROV-O (W3C Provenance Ontology) metadata
- A promotion log showing entity counts, matching methods, and confidence distribution
- WealthSignal instances derived from promoted data via SPARQL CONSTRUCT
- `ontology/extensions/prov-o-bindings.ttl` — PROV-O vocabulary for the promotion path

The notebook is `notebooks/05_entity_resolution.ipynb`.

## How This Connects to Competency Questions

In Module 1, you wrote Competency Questions (CQs) — the testable questions your
ontology must answer. Module 5 is where those questions start getting answered with
*real data* rather than a minimal test graph.

When you promote entities from the LGD (Lexical Graph Database) to the SLGD, the
promoted data must be able to answer the same CQs. For example:
- CQ1 ("Which customers have generated a wealth signal?") requires promoted
  Customer entities to exist in the SLGD
- CQ3 ("Which household relationships does this customer have?") requires the
  household membership links to survive promotion

The WealthSignal derivation at the end of this module is the first time the
architecture *computes* answers to CQs from real data — signals are derived from
promoted transactions, not loaded from a file. This is the "computed, not loaded"
principle in action: CQs are answered by running queries against derived data.

## Steps

Before running any code, read cell 1 of the notebook — it contains the module
introduction and a Key Terms table. The vocabulary defined there is referenced
throughout the rest of the module.

### Step 1 — Open the notebook and retrieve endpoints

Open `notebooks/05_entity_resolution.ipynb`. Run cell 2 (setup) to connect to
the Neptune clusters deployed in Module 3.

Run cell 2. Expected output:

```
ATLAS Module 5 — Entity Resolution and the Promotion Path
Synthetic data seed: 42

Neptune LGD:  atlas-lgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
Neptune SLGD: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
```

### Step 2 — Read the Entity Resolution explanation

Read cell 3 carefully. It explains:
- What entity resolution is (determining that records from different sources refer
  to the same real-world entity)
- The difference between rule-based matching (deterministic, confidence 1.0) and
  ML-based matching (probabilistic, confidence < 1.0)
- Why the workshop uses a simplified ER approach to focus on the promotion path

### Step 3 — Run the Entity Resolution simulation

Run cell 4 to simulate entity resolution across the synthetic data sources.

Run cell 4. Expected output:

```
Entity Resolution Results
============================================================
Total entities resolved: 200
  Rule-based matches: 185 (confidence: 1.0)
  ML-based matches:   15 (confidence: 0.75 - 0.98)
```

### Step 4 — Read the "Outputs Are Computed, Not Loaded" section

Read cell 5b. This explains the critical architectural principle: ATLAS produces
signals from data the customer already has. No pre-computed signal instances are
loaded from external files.

### Step 5 — Run the Promotion Script

Run cell 6 to execute the governed promotion path. This generates PROV-O-attributed
triples for each resolved entity and writes them to the SLGD (if Neptune is reachable).

Run cell 6. Expected output:

```
Promotion Path Execution
============================================================
Run ID:    promotion-YYYYMMDD-HHMMSS
Timestamp: 2026-05-11T...Z
Operator:  workshop-participant
Neptune:   reachable

Entities to promote: 200
Triples generated:   1403
Writing to SLGD...
  Written: 1403 triples

Promotion complete.
```

### Step 6 — Review the Promotion Log

Run cell 7 to generate the promotion log with confidence distribution.

### Step 7 — Run the Validation Gate

Run cell 9 (Module 5 validation gate).

Run cell 9. Expected output:

```
============================================================
MODULE 5 VALIDATION GATE
============================================================
[PASS] Gate 1 - 200 entities have promotedFrom (provenance)
[PASS] Gate 2 - 200 entities have promotedBy (activity link)
[PASS] Gate 3 - 200 entities have confidence score
[PASS] Gate 4 - Promotion activity has timestamp and operator
[PASS] Gate 5 - 200 entities promoted (expected >= 200)

MODULE 5 VALIDATION: PASS
You may proceed to Module 6.
```

### Step 6b — Promote account and transaction entities (cell 06b)

Run cell 06b (`cell-06b-promote-accounts`) to promote Account and Transaction nodes to the
SLGD with `-resolved` URIs and PROV-O provenance. This also writes `atlas:hasAccount` and
`atlas:hasTransaction` links from promoted customer and account nodes.

### Step 6c — Promote advisory relationships (cell 06c)

Run cell 06c (`cell-06c-promote-advisory-rels`) to promote AdvisoryRelationship and Advisor
nodes to the SLGD. This writes `atlas:hasAdvisor` links and coverage date attributes needed
by the signal derivation coverage filter.

### Step 6d — Promote household membership (cell 06d)

Run cell 06d (`cell-06d-promote-households`) to write `atlas:memberOf` links from every
promoted customer to their household node, and to type each household node as
`atlas:Household`.

**Why this step is required:** the HouseholdAggregationSignal derivation query in cell 9f
opens with `?customer atlas:memberOf ?household`. If this cell has not run, that pattern
matches zero rows and the household signal branch produces zero signals — silently, without
an error. Cell 06d must run before cell 09f for household signals to fire.

Expected output:

```
Household membership promotion triples: 263
  atlas:memberOf links (one per customer):  200
  atlas:Household type nodes (unique):       63
  Written: 263 triples
```

### Step 8 — Run the live WealthSignal Derivation (cell 9f)

Run cell 9f (`cell-09f-derive-signals-live`) to derive WealthSignal instances from the
promoted data in the live SLGD and write them back. This cell reads actual account
balances and coverage status from the graph — not from the simulation above.

**Run order dependency:** cells 06, 06b, 06c, and 06d must all have run before this cell.
If cell 06d was skipped, the household signal branch will produce zero signals. Re-run
order: 06d → 09f → 09g.

**What it produces:**

Two signal types are derived:

- **LargeDepositPattern** — fires when a customer's promoted transaction data shows a
  single deposit of $250,000 or more within the 90-day observation window, and the
  customer has no active wealth advisor coverage. The threshold is set by your risk
  team; the rule is version-controlled SPARQL.

- **HouseholdAggregationSignal** — fires when a household's combined checking and
  savings balances reach $1,000,000, no single member holds that much alone, and
  coverage is mixed (some members have an active wealth advisor, some do not).

**Which customers receive the household signal:** The `atlas:producesSignal` link is
attached to the **uncovered** household members only — not to all members. The reason
is that the signal exists to drive a referral, and the referral target is the member
who does not yet have an active wealth advisor. Surfacing the signal on a covered
member would show an alert whose only available action ("refer to wealth") does not
apply. The signal is actionable wherever it appears; it only appears where action is
needed.

**Practical consequence:** if you look up a covered member of a qualifying household,
you will not see the household signal on their record. This is the correct behavior.
The signal is visible on the uncovered member(s) in the same household.

Expected output:

```
Signal 1: LargeDepositPattern
  [PASS] LargeDepositPattern: N triples SHACL-validated and written to SLGD

Signal 2: HouseholdAggregationSignal
  Qualifying households (all 3 conditions): N
  [PASS] HouseholdAggregationSignal: N triples SHACL-validated and written to SLGD

Total signal triples written to SLGD: N
```

Exact counts vary by the current date (the 90-day window shifts). The numbers are
printed by the cell — they are derived, not asserted.

## Expected Outputs

- SLGD populated with 200 resolved Customer entities, each with PROV-O metadata
- Account and Transaction entities promoted with `-resolved` URIs and provenance
- Advisory relationships promoted, enabling coverage-aware signal detection
- WealthSignal instances derived from live promoted data (LargeDeposit + HouseholdAgg)
- Module 5 validation gate prints `MODULE 5 VALIDATION: PASS`

## Troubleshooting

**Neptune not reachable**

The notebook gracefully handles this case — it generates triples locally and reports
what would be written. Run from SageMaker (inside the VPC) for full execution.

**Gate 3 fails with "Only N entities have confidence"**

Check that the confidence value uses the correct XSD datatype (`XMLSchema#decimal`).
The gate checks for this specific string in the generated triples.

**Cell 6 fails with "SSL: CERTIFICATE_VERIFY_FAILED"**

Neptune's TLS certificate is signed by the Amazon RDS CA, which is included in the
`certifi` bundle that ships with the SageMaker Studio Python environment. Do not
disable certificate verification. If you see this error, confirm that the
`SLGD_ENDPOINT` variable matches the cluster endpoint exactly (no trailing slash,
no port suffix) so the hostname matches the certificate's Common Name.

## What's Next

Module 5 promoted data to the SLGD with provenance. Module 6 asks: how do we
mechanically enforce that probabilistic outputs never flow into compliance-bound
paths without explanation? The answer is SHACL shapes — machine-checkable rules
that validate the boundary between deterministic and probabilistic components.
