---
title: "Module 6 — SHACL: Making the Boundary Mechanical"
weight: 60
---

# Module 6 — SHACL: Making the Boundary Mechanical

## Learning Objectives

- Explain what SHACL (Shapes Constraint Language) is and why it matters for
  regulated architectures
- Write SHACL shapes that enforce the deterministic-vs-probabilistic boundary
- Run the SHACL validator against both conforming and non-conforming graphs
  and interpret the validation report
- Demonstrate to a Model Risk Management reviewer that the boundary is enforced
  mechanically, not by convention

## Time Estimate

45 to 60 minutes.

## Prerequisites

- Module 5 complete (SLGD populated with promoted data)
- `ontology/atlas-shapes.ttl` present in the repository

## What You Will Build

This module produces:

- `ontology/atlas-shapes.ttl` — six SHACL shapes enforcing the boundary
- A validation report showing the shapes catch boundary violations
- A counter-example demonstrating what happens when probabilistic data enters
  a compliance-bound path without explanation
- Evidence that a reviewer can run one command and produce a compliance report

The notebook is `notebooks/06_shacl_boundary.ipynb`.

## Steps

### Step 1 — Open the notebook and load the shapes

Open `notebooks/06_shacl_boundary.ipynb`. Run cell 2 to load the SHACL shapes
file and the ontology.

Run cell 2. Expected output:

```
ATLAS Module 6 — SHACL: Making the Boundary Mechanical
Shapes loaded: 6 shapes from ontology/atlas-shapes.ttl
Ontology loaded: atlas-core.ttl + atlas-fibo-alignment.ttl
```

### Step 2 — Read the SHACL introduction

Read cells 3 and 4. These explain:
- What SHACL is (a W3C standard for validating RDF graphs against constraints)
- Why SHACL matters for MRM (it makes the boundary machine-checkable)
- The six shapes in ATLAS and what each one enforces

### Step 3 — Validate the conforming graph

Run cell 4 to validate the promoted SLGD data against the SHACL shapes.
A conforming graph should pass all shapes.

Run cell 4. Expected output:

```
Validating conforming graph against SHACL shapes...
  Conforms: True
  Violations: 0

[PASS] The promoted data conforms to all 6 SHACL shapes.
```

### Step 4 — Run the counter-example

Run cell 6 to construct a deliberately non-conforming graph (one that violates
the boundary) and validate it. This demonstrates what the shapes catch.

Run cell 6. Expected output:

```
Counter-example: Probabilistic score without explainability flag
------------------------------------------------------------
Validating non-conforming graph...
  Conforms: False
  Violations: 1

  Violation 1:
    Focus node: inst:score-bad-example
    Shape: atlas:ScoreExplainabilityShape
    Message: A Score used in a compliance path must have explainability=true
```

### Step 5 — Review the routing-policy shape

Run cell 8 to demonstrate the routing-policy shape that enforces the closed
route enumeration. This shape prevents the LLM from inventing routes.

### Step 6 — Run the validation gate

Run cell 10 (Module 6 validation gate).

Run cell 10. Expected output:

```
============================================================
MODULE 6 VALIDATION GATE
============================================================
[PASS] Gate 1 — 6 SHACL shapes loaded
[PASS] Gate 2 — Conforming graph passes validation
[PASS] Gate 3 — Counter-example fails validation (expected)
[PASS] Gate 4 — Routing-policy shape enforces closed set
[PASS] Gate 5 — atlas-shapes.ttl is valid Turtle

MODULE 6 VALIDATION: PASS
You may proceed to Module 7.
```

## Expected Outputs

- `ontology/atlas-shapes.ttl` — six SHACL shapes (already present in repo)
- Validation report showing conforming data passes
- Counter-example showing non-conforming data fails
- Module 6 validation gate prints `MODULE 6 VALIDATION: PASS`

## Troubleshooting

**pyshacl raises ImportError**

Run `pip install pyshacl==0.25.0` in your terminal. The package should have been
installed during the prerequisites step.

**Validation reports "Conforms: False" on the conforming graph**

Check that the promoted data from Module 5 includes the required `atlas:explainability`
and `atlas:probabilistic` flags on Score instances. Re-run Module 5 cell 6 if needed.

## What's Next

Module 6 established the mechanical boundary. Module 7 introduces the LLM into the
architecture — but in a sharply circumscribed role. Bedrock translates between human
language and SPARQL queries. Every generated query is validated before execution.
The LLM does not reason, score, or make decisions.
