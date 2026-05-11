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
- A demonstration script suitable for presenting to a CIO

The notebook is `notebooks/08_wealth_signal_demo.ipynb`.

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
