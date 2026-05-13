---
title: "Module 2 — FIBO Alignment and the Extension Ring"
weight: 20
---

# Module 2 — FIBO Alignment and the Extension Ring

## Learning Objectives

- Navigate FIBO's module structure (FND, BE, FBC, SEC, LOAN, DER) and identify
  which module to open for a given financial services concept
- Bind an institution-specific ontology class to a FIBO IRI using `rdfs:subClassOf`
  and explain why `subClassOf` is correct and `owl:equivalentClass` is almost always
  wrong for institution-specific ontologies
- Identify concepts that FIBO deliberately does not cover and select the appropriate
  extension standard (PROV-O, DCAT, SKOS, GLEIF, ISO 20022, BIAN) for each gap
- Produce a FIBO alignment file and a gaps document that together account for every
  class in the ontology
- Demonstrate a GLEIF/LEI binding for an institutional counterparty via FIBO BE

## Time Estimate

60 to 75 minutes.

## Prerequisites

- Module 1 complete (`ontology/atlas-core.ttl` and `ontology/rationale.md` present)
- Module 1 validation gate passed
- Internet access from the SageMaker notebook (optional — for FIBO documentation
  browsing; the notebook works offline with pinned IRIs)
- Amazon Bedrock enabled in us-east-1 (optional — for the FIBO exploration exercise)

## What You Will Build

This module produces two deliverables:

1. `ontology/atlas-fibo-alignment.ttl` — a Turtle file that binds every atlas-core
   class to its FIBO counterpart (where one exists) using `rdfs:subClassOf`, plus
   extension-ring bindings to PROV-O (W3C Provenance Ontology), DCAT (Data Catalog
   Vocabulary), and SKOS (Simple Knowledge Organization System) for classes that
   FIBO does not cover
2. `ontology/alignment-gaps.md` — a Markdown document listing every atlas-core class
   that does NOT have a FIBO counterpart, with the rationale for why FIBO is silent
   and the chosen extension standard (if any)

The module also introduces three new classes not in atlas-core.ttl:
`atlas:LegalEntity`, `atlas:Product`, and `atlas:LineOfBusiness` — each with
immediate FIBO bindings.

## How This Connects to Competency Questions

In Module 1, you wrote Competency Questions (CQs) that define what the ontology
must answer. FIBO alignment does not change those questions — it changes the
*vocabulary* used to answer them. After this module, a SPARQL query for CQ1
("Which customers have generated a wealth signal?") still works, but the
`atlas:Customer` class now carries a formal relationship to FIBO's
`IndependentParty`. This means your CQ answers are interoperable with any other
system that aligns to FIBO.

The key insight: **Competency Questions are stable across alignment.** If aligning
to FIBO broke a CQ query, the alignment would be wrong. The Module 2 validation
gate confirms this — it checks that the merged ontology still parses correctly,
which means your CQ queries from Module 1 remain valid.

## Steps

### Step 1 — Open the notebook and load the Module 1 ontology

Open `notebooks/02_fibo_alignment.ipynb` in your SageMaker instance. Run cell 3
(setup) to load `atlas-core.ttl` and confirm all 18 classes are present.

![Module 2 notebook open with class list](/static/images/02-step-01-notebook-open.png)

Run cell 3. Expected output:

```
rdflib   : 7.0.0
pyshacl  : 0.25.0

Module 1 ontology loaded: 18 classes
Source: ../ontology/atlas-core.ttl
   1. atlas:Account
   2. atlas:Advisor
  ...
  18. atlas:WorkflowStep
```

### Step 2 — Read the FIBO overview and module walkthrough

Read cells 4 and 5 carefully. These are the teaching cells — they walk through
FIBO's module structure and explain which ATLAS classes bind where and why.

Key concepts to understand before proceeding:
- FIBO is organised into modules (FND, BE, FBC, SEC, LOAN, DER)
- A FIBO IRI encodes the module path: `fibo/ontology/FND/Parties/Parties/IndependentParty`
- We pin to FIBO 2024 Q3 Production Release (not Development)
- FIBO is an alignment vocabulary, not a replacement for your ontology

### Step 3 — Understand subClassOf vs equivalentClass

Read cell 6. This is the single most important design decision in FIBO alignment.

The rule: use `rdfs:subClassOf` unless you can prove that your class and the FIBO
class have identical membership. In practice, this means almost always `subClassOf`,
because your institution adds constraints that FIBO does not require.

### Step 4 — Review the three worked bindings

Read cell 7. Three bindings are shown in full Turtle syntax:
1. Customer → `fibo-fnd-pty-pty:IndependentParty`
2. Account → `fibo-fbc-pas-fpas:FinancialAccount`
3. Holding → `fibo-fbc-fi-ip:InvestmentPosition`

Each binding includes a comment explaining the narrowing — what constraint ATLAS
adds that FIBO does not require.

### Step 5 — Load and inspect the alignment file

Run cell 8 to load `atlas-fibo-alignment.ttl` and display all bindings.

![Alignment bindings displayed](/static/images/02-step-05-alignment-loaded.png)

Run cell 8. Expected output:

```
Alignment file loaded: NN triples
Source: ../ontology/atlas-fibo-alignment.ttl

FIBO/Extension bindings found: 12

ATLAS Class                Bound To
------------------------------------------------------------------------------------------
  atlas:Account              fibo:FBC/ProductsAndServices/...
  atlas:Advisor              fibo:FND/Parties/Roles/...
  ...
```

### Step 6 — Review the extension ring

Read cell 9. The extension ring is the set of standards that cover what FIBO does not:
- PROV-O for provenance
- DCAT for data sources
- SKOS for controlled vocabularies
- GLEIF/LEI for legal entity identifiers
- ISO 20022 for payment message structure
- BIAN for operating-model terminology

### Step 7 — Run the classification check

Run cell 10 to see every atlas-core class classified as FIBO-bound, extension-ring-bound,
or bank-specific.

![Classification output](/static/images/02-step-07-classification.png)

Run cell 10. Expected output:

```
ATLAS Class Alignment Classification
======================================================================

FIBO-BOUND (direct subClassOf a FIBO Production class):
  atlas:Account                -> fibo-fbc-pas-fpas:FinancialAccount
  atlas:Advisor                -> fibo-fnd-pty-rl:FunctionalRole
  ...

EXTENSION-RING-BOUND (subClassOf a W3C/industry standard class):
  atlas:AuditRecord            -> prov:Entity (PROV-O)
  atlas:DataSource             -> dcat:Dataset (DCAT v3)
  ...

BANK-SPECIFIC (no external binding; documented in alignment-gaps.md):
  atlas:Eligibility
  atlas:Household
  ...

Total classified: 21
```

### Step 8 — Run the GLEIF/LEI demonstration

Run cell 12 to see how an institutional counterparty is bound to FIBO BE via LEI.

Run cell 12. Expected output:

```
GLEIF/LEI Binding Demonstration
============================================================

Entity:  Acme Financial Holdings LLC
LEI:     5493001KJTIIGC8Y1R12
Type:    atlas:LegalEntity
Aligned: rdfs:subClassOf fibo-be-le-lei:LegalPerson
```

### Step 9 — Verify the gaps document

Run cell 14 to confirm that `alignment-gaps.md` documents all bank-specific classes.

Run cell 14. Expected output:

```
Alignment Gaps Document Check
============================================================
File: ../ontology/alignment-gaps.md
Size: NNNN characters

[PASS] All 9 bank-specific classes documented in alignment-gaps.md
```

### Step 10 — Run the validation gate

Run cell 20 (the Module 2 validation gate). All five sub-gates must pass.

![Module 2 validation gate PASS](/static/images/02-step-10-validation-pass.png)

Run cell 20. Expected output:

```
============================================================
MODULE 2 VALIDATION GATE
============================================================
[PASS] Gate 1 — atlas-fibo-alignment.ttl parses (NN triples)
[PASS] Gate 2 — All 18 core classes accounted for
         Bound to external IRI: 9
         Documented in gaps:    9
[PASS] Gate 3 — No contradictions (no class is both bound and in gaps)
[PASS] Gate 4 — alignment-gaps.md present (NNNN chars)
[PASS] Gate 5 — FIBO version (2024 Q3) documented in alignment file

MODULE 2 VALIDATION: PASS
You may proceed to Module 3.
```

## Expected Outputs

After running all cells in `notebooks/02_fibo_alignment.ipynb`:

- `ontology/atlas-fibo-alignment.ttl` — present; contains `rdfs:subClassOf` bindings
  to FIBO and extension-ring standards
- `ontology/alignment-gaps.md` — present; documents all bank-specific classes
- Module 2 validation gate (cell 20) prints `MODULE 2 VALIDATION: PASS`

## Troubleshooting

**Cell 8 fails with "No such file or directory" for atlas-fibo-alignment.ttl**

The alignment file should already be in the repository at `ontology/atlas-fibo-alignment.ttl`.
If it is missing, confirm you have the latest version of the repo. The file is committed
as part of the Module 2 deliverable.

**Cell 16 (Bedrock FIBO exploration) fails with AccessDeniedException**

This cell is optional. The alignment file is already complete — the Bedrock cell is
a learning exercise for exploring FIBO with LLM assistance. If Bedrock is not available,
skip this cell and continue to cell 17.

**Gate 2 fails with "class neither bound nor documented"**

A class in `atlas-core.ttl` is missing from both `atlas-fibo-alignment.ttl` and
`alignment-gaps.md`. Check which class is reported and add either a binding (if a
FIBO counterpart exists) or a gaps entry (if it does not).

**Gate 3 fails with "contradictions found"**

A class appears in both the alignment file (with a binding) and the gaps document.
Remove it from one or the other. If it has a valid `rdfs:subClassOf` binding, remove
it from gaps. If the binding is incorrect, remove it from the alignment file and
document it in gaps.

## Extending This to Your Data

The appendix in the notebook (cell 21) provides a checklist for FIBO alignment in
your own context: which FIBO modules to import for which lines of business, how to
handle the case where two FIBO classes both look like candidates for binding, and
the most common gotcha — confusing FIBO's IndependentParty with its more specific
subclasses, which leads to over-constrained bindings that fail when a customer is
also a small business.

The decision framework for future gaps: if a W3C standard covers it, use the standard.
If an industry standard covers it, use the standard. If it is institution-specific,
model it as a bank-specific class with clear documentation.

## What's Next

Module 2 produced the aligned ontology — classes bound to FIBO, gaps documented,
extension ring identified. Module 3 asks: does this ontology work as a physical
graph? It deploys two Amazon Neptune clusters (LGD and SLGD), loads the aligned
ontology into the SLGD, and runs SPARQL discovery queries that confirm the
FIBO-aligned classes are queryable. The LGD/SLGD split — raw versus curated,
unvalidated versus SHACL-enforced — becomes a physical reality rather than a diagram.
