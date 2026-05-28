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

- `ontology/atlas-shapes.ttl` — six SHACL (Shapes Constraint Language) shapes
  enforcing the boundary
- A validation report showing the shapes catch boundary violations
- A counter-example demonstrating what happens when probabilistic data enters
  a compliance-bound path without explanation
- Evidence that a reviewer can run one command and produce a compliance report

The notebook is `notebooks/06_shacl_boundary.ipynb`.

## How This Connects to Competency Questions

In Module 1, you wrote Competency Questions (CQs) that test whether the ontology
has the right structure. SHACL shapes are a complementary validation mechanism —
they test whether the *data* in the graph conforms to the rules the ontology implies.

Think of it this way:
- **CQs validate structure** — "Can the ontology answer this question?" (Module 1)
- **SHACL validates content** — "Does the data in the graph follow the rules?" (Module 6)

For example, CQ2 asks about the "deterministic vs probabilistic component" of a
score. The CQ proves the ontology *can* distinguish these. The SHACL shape in this
module *enforces* that every Score instance actually carries the required
`explainability` flag. CQs define what's possible; SHACL enforces what's required.

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

## The SR 11-7 connection

The shapes you ran in this module are not abstract data quality rules. They are
the architectural primitive that satisfies a specific clause of US bank
supervisory guidance.

**SR 11-7** (Federal Reserve, "Guidance on Model Risk Management") and the
parallel **OCC Bulletin 2011-12** require that any model used in consequential
banking decisions be:

1. **Reproducible** — the same inputs must produce the same outputs, and the
   model artifact must be versioned and retrievable.
2. **Subject to independent validation** — a party other than the model
   developer must be able to verify the model's behavior on holdout data.
3. **Bounded in its effects** — the model's outputs must not silently influence
   decisions outside its validated scope.

The ATLAS SHACL boundary addresses clause (3) at the data layer. The
`atlas:ScoreExplainabilityShape` you ran in Step 4 enforces that every Score node
carrying probabilistic output must declare `atlas:probabilistic=true` and carry
an `atlas:confidence` value. The counter-example in cell 6 demonstrates exactly
what the shape catches: a probabilistic score attempting to enter the SLGD
without its explainability metadata. The graph database rejects the write.

This is the SR 11-7 boundary expressed as code. A probabilistic model output
cannot silently cross into the deterministic decision path. The boundary is
not enforced by policy documentation or by reviewer vigilance — it is enforced
by `pyshacl` refusing to mark the graph as conforming and by Neptune refusing
to accept the write.

For an MRM reviewer, this is a defensible artifact: "show me a write that
violates the boundary" can be answered with a real example (Step 4) and a
real rejection.

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
