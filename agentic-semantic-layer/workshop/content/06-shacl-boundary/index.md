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
- A plain-English shape-explanation document at `docs/model-risk-review.md` for MRM reviewers (143 lines, hand-authored — covers each shape's purpose, what a violation looks like, and how to fix it)

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

### Step 1 — Open the notebook and read the Key Terms

Open `notebooks/06_shacl_boundary.ipynb`. Read cell 1 (the module introduction
and Key Terms table). This module introduces dense vocabulary — SHACL, shapes,
conformance, violations, target classes, validation reports, plus the regulatory
acronyms SR 11-7 and OCC 2011-12. Pause on the Key Terms cell before running
any code.

### Step 2 — Read the counter-example introduction (cells 1b and 3)

Read cell 1b (How This Connects to Competency Questions) and cell 3 ("The
Counter-Example: Why SHACL Exists"). Cell 3 sets up the teaching approach:
we build a deliberately bad graph first, show what a compliance query returns
without shapes (a confident-looking number with no provenance), then introduce
the shapes that catch it. Understanding the pain before the solution is the
module's teaching structure.

### Step 3 — Build the counter-example (cell 4)

Run cell 4. This constructs a Score node with no provenance, no confidence
value, no model version, no explainability flag — the kind of write the SHACL
boundary is designed to prevent. It also runs a bare SPARQL query against the
bad graph to show that, without shapes, the query returns a result as if the
data were valid.

Expected output (excerpt):

```
Without SHACL: bare compliance query returns a result from an
unattributed probabilistic score.
  score-BAD-001: 0.87

This is the problem. The number looks fine. SHACL exists to
make the missing provenance visible.
```

### Step 4 — Read the six shapes table (cell 5)

Read cell 5 (markdown). It introduces the six shapes in ATLAS and what each
enforces: ProvenanceShape, BoundaryShape, ComplianceInputShape,
RoutingPolicyShape, WealthSignalTypeShape, and CoverageRelationshipShape.
No code to run — this cell is the vocabulary for what the validator will report.

### Step 5 — Write the shapes file and validate the counter-example (cells 6 and 8)

Run cell 6. This writes `ontology/atlas-shapes.ttl` with all six shapes. The
file is written to the repository path — you can open it in a text editor to
inspect the Turtle syntax.

Expected output:

```
SHACL shapes file written: ontology/atlas-shapes.ttl
  6 shapes defined
```

Then run cell 8. This loads the shapes file and validates the counter-example
graph from cell 4. The bad graph should fail validation.

Expected output:

```
Validating counter-example (BAD graph) against SHACL shapes...
============================================================
Conforms: False

VIOLATIONS FOUND (this is expected - the counter-example is deliberately bad):
...
The validator caught the missing attributes. This is exactly what SHACL
is for: making the boundary mechanical rather than conventional.
```

### Step 6 — Validate correct data (cell 10)

Run cell 10. This builds a properly attributed graph — a Score with all
required fields (confidence, model version, explainability flag, PROV-O
attribution) — and confirms it passes all shapes.

Expected output (excerpt):

```
Validating GOOD graph against SHACL shapes...
Conforms: True
Good graph passes all 6 SHACL shapes.
```

### Step 7 — Run the validation gate (cell 12)

Run cell 12 (Module 6 validation gate).

Expected output:

```
============================================================
MODULE 6 VALIDATION GATE
============================================================
[PASS] Gate 1 - atlas-shapes.ttl parses (N triples)
[PASS] Gate 2 - Counter-example correctly fails validation
[PASS] Gate 3 - Good graph correctly passes validation
[PASS] Gate 4 - All 6 shape categories present
[PASS] Gate 5 - Shapes file is N bytes (non-trivial)

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
