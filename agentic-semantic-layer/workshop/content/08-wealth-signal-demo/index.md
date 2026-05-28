---
title: "Module 8 — The Wealth-Signal Demo with Bounded Agent"
weight: 80
---

# Module 8 — The Wealth-Signal Demo with Bounded Agent

## Learning Objectives

- Demonstrate the end-to-end wealth-signal workflow to a CIO
- Explain how the bounded agent selects routes from an enumerated set (not by LLM reasoning)
- Show the full audit trail from signal detection through advisor approval in SPARQL
- Explain the two outputs of the workflow: HumanReview (engagement event) and
  AdvisoryRelationship (coverage assertion)
- Explain why every component in the workflow is classified as deterministic,
  probabilistic-explainable, or probabilistic-opaque

## Time Estimate

45 to 60 minutes.

## Prerequisites

- All prior modules complete (Modules 1–7)
- Neptune clusters running with ontology and promoted data
- Bedrock access for narrative drafting

## What You Will Build

This module produces:

- A simulated end-to-end workflow execution (signal → score → route → review → approve)
- An AdvisoryRelationship minted on approval (coverage assertion with provenance)
- The full audit trail queryable in one SPARQL query (the CIO demo)
- A demonstration script suitable for presenting to a CIO (Chief Information Officer)

The notebook is `notebooks/08_wealth_signal_demo.ipynb`.

## How This Connects to Competency Questions

This is the payoff. The Competency Questions (CQs) you wrote in Module 1 were
acceptance tests for an empty ontology. In Module 8, those same questions are
answered by a running system with real (synthetic) data flowing through it.

The CIO demo query in this module is essentially **CQ6** ("What is the full audit
trail from signal detection to advisor approval?") running against the SLGD
(Semantic Layer Graph Database) with promoted, scored, routed, and reviewed data.
One SPARQL query. Full audit trail. Every component classified.

This completes the Competency Question lifecycle:

| Module | CQ Role | What Happens |
|--------|---------|--------------|
| 1 | **Validation** | CQs prove the ontology has the right structure |
| 2 | **Stability** | CQs remain valid after FIBO alignment |
| 5 | **Derivation** | CQs are answered by computed (not loaded) data |
| 6 | **Enforcement** | SHACL shapes enforce what CQs imply |
| 7 | **Grounding + Accuracy** | CQs become few-shot examples and benchmarks for the LLM |
| 8 | **Proof of value** | CQs are answered end-to-end in a live demo |

## Steps

### Step 1 — Open the notebook and review the workflow

Open `notebooks/08_wealth_signal_demo.ipynb`. Read cell 1 (the module introduction)
to understand the end-to-end workflow and the bounded agent pattern.

Run cell 2 (setup). Expected output:

```
Module 8 — The Wealth-Signal Demo with Bounded Agent
Synthetic data seed: 42
Demo persona: Alex Morgan (Wealth Advisor)
```

### Step 2 — Simulate the wealth-eligibility event

Run cell 4 to detect a wealth-eligibility event from the synthetic transaction data.

Run cell 4. Expected output:

```
Step 1: Wealth-Eligibility Event Detected
============================================================
  Customer:    [Name]
  Signal type: large-deposit-pattern
  Amount:      $XXX,XXX.XX
  Event written to LGD as atlas:BehavioralEvent
  EventBridge rule fires -> Step Functions state machine starts
```

### Step 3 — Enrich and score

Run cell 6 to simulate the bounded agent enriching the event with household context
and calling the XGBoost scoring endpoint.

Run cell 6. Expected output:

```
Step 2: Bounded Agent Enriches and Scores
============================================================
  Household enrichment:
    Members in household: N
    Combined balance:     $X,XXX,XXX.XX

  XGBoost Score:
    Wealth-conversion probability: 0.XXX
    Component class: PROBABILISTIC-EXPLAINABLE

  SHAP Feature Attributions:
    deposit_amount            0.XXX ###########
    household_balance         0.XXX ########
    ...
```

### Step 4 — Route selection

Run cell 8 to demonstrate deterministic route selection from the closed enumerated set.

### Step 5 — Human-in-the-loop review

Run cell 10 to simulate Alex Morgan reviewing and approving the lead.

### Step 6 — Write the audit trail and mint AdvisoryRelationship

Run cell 12. This is the key cell — on APPROVED outcome, it:
1. Writes the full audit trail to the SLGD
2. Mints an `atlas:AdvisoryRelationship` with:
   - `coveringAdvisor` from `HumanReview.conductedBy`
   - `advisesCustomer` from the target customer
   - `coverageStartDate` from `reviewDate`
   - `relationshipType` = `RelType_Primary`
   - `prov:wasGeneratedBy` pointing to the HumanReview

Run cell 12. Expected output:

```
Step 5: Audit Trail Written to SLGD
============================================================
  APPROVED branch: AdvisoryRelationship minted
    coveringAdvisor:   Alex Morgan (from HumanReview.conductedBy)
    advisesCustomer:   [Customer Name]
    coverageStartDate: YYYY-MM-DD (from reviewDate)
    relationshipType:  RelType_Primary
    prov:wasGeneratedBy -> HumanReview (engagement -> coverage link)

  Audit trail triples generated: NN
```

### Engagement vs Coverage: the two outputs of Module 8

When the workflow approves a lead, two distinct kinds of artifacts are written
to the SLGD:

1. **HumanReview** (the *engagement event*) — records what happened: who
   reviewed, when, what the outcome was. This is a PROV-O activity in the
   audit chain. It answers: "what actions were taken on this signal?"

2. **AdvisoryRelationship** (the *coverage assertion*) — records who is
   responsible: which advisor covers this customer, starting when, under what
   relationship type. This is a standing assignment that persists beyond the
   workflow execution. It answers: "who is this customer's advisor right now?"

The distinction matters because:

- **Engagement is an event chain.** It has a start, a middle, and an end.
  Once the workflow closes, the HumanReview is historical.
- **Coverage is a standing assertion.** It remains active until explicitly ended.
  It is what downstream systems (CRM, communications, reporting) query when
  routing future interactions with the customer.

Coverage is *derived from* engagement: the `atlas:AdvisoryRelationship` is
minted with `prov:wasGeneratedBy` pointing back to the HumanReview that created
it. This means you can always trace a coverage assignment back to the engagement
event that authorized it.

**Two provenance patterns coexist in the SLGD:**

- **Workflow-minted coverage** (the Module 8 path): `prov:wasGeneratedBy ?humanReview`
  — created by an APPROVED HumanReview outcome.
- **Legacy coverage** (pre-existing): `prov:wasAttributedTo atlas:LegacyDataMigration`
  — migrated from the institution's prior systems. The 105 entries in
  `data/synthetic/advisory-relationships.json` carry this stamp; they predate
  the ATLAS workflow.

A query like "show me all coverage assignments created in the last 90 days by
this workflow" against the SLGD filters on `prov:wasGeneratedBy` and excludes
legacy data. The provenance stamp is the disambiguator. For MRM and audit,
this distinction is not optional — workflow-minted coverage has a full audit
chain back to a human decision; legacy coverage has a different (and shorter)
attribution.

### Step 7 — Run the CIO demo query

Run cell 14 to execute the one-query audit trail — the query you show a CIO.

Run cell 14. Expected output:

```
The CIO Demo Query
============================================================

"Show me the complete path from signal detection to advisor approval."

  Signal type:    LargeDepositPattern
  Score:          0.XXX
  Route:          ROUTE_ADVISOR_QUEUE
  Review outcome: APPROVED
  Advisor:        advisor-alex-morgan

This is what the reader demos to a CIO at the end of Module 8.
One query. Full audit trail. Every component classified.
```

### Step 8 — Run the validation gate

Run cell 15 (Module 8 validation gate).

Run cell 15. Expected output:

```
============================================================
MODULE 8 VALIDATION GATE
============================================================
[PASS] Gate 1.1 - WealthSignal in audit trail
[PASS] Gate 1.2 - Score in audit trail
[PASS] Gate 1.3 - RoutingDecision in audit trail
[PASS] Gate 1.4 - HumanReview in audit trail
[PASS] Gate 1.5 - Advisor in audit trail
[PASS] Gate 1.6 - AdvisoryRelationship in audit trail
[PASS] Gate 2 - Score has explainability=true (SHAP)
[PASS] Gate 3 - Route from closed enumerated set
[PASS] Gate 4 - HumanReview has outcome + advisor
[PASS] Gate 4b - AdvisoryRelationship has coveringAdvisor, advisesCustomer, ...
[PASS] Gate 5 - CIO demo query returns results

MODULE 8 VALIDATION: PASS

Congratulations. You have completed the ATLAS workshop.
```

## Expected Outputs

- End-to-end workflow simulation complete
- AdvisoryRelationship minted with full provenance
- CIO demo query returns the complete audit trail
- Module 8 validation gate prints `MODULE 8 VALIDATION: PASS`

## Troubleshooting

**Cell 4 fails with "StopIteration" (no signal transaction found)**

The synthetic data generator uses a fixed seed. If you modified `atlas_synthetic.py`
or changed the seed, the signal-tagged transactions may not exist. Reset to seed 42.

**CIO demo query returns no results**

Check that cell 12 ran successfully and generated audit trail triples. The query
runs against the in-memory graph built from those triples.

## What's Next

**Congratulations — you have completed the ATLAS workshop.**

You can now:
1. Articulate why the deterministic-vs-probabilistic boundary matters
2. Build this pattern in your own account against your own data
3. Defend the architecture in front of an MRM reviewer
4. Extend the ontology with your institution's concepts

Proceed to [Cleanup](../99-cleanup/) to tear down all infrastructure and stop costs.
