# ATLAS Model Risk Review — SHACL Shape Explanations

This document explains each SHACL shape in plain English for a Model Risk
Management (MRM) reviewer who has not read Turtle syntax. Each shape is a
machine-checkable rule that the ATLAS system enforces continuously.

## How to use this document

Run the SHACL validator against the SLGD (Semantic Layer Graph Database):
```bash
pyshacl --shacl ontology/atlas-shapes.ttl --data <slgd-export.ttl>
```

The validator produces a report listing any violations. This document explains
what each shape enforces and why a violation matters.

---

## Shape 1: ProvenanceShape

**What it constrains:** Every Customer node in the SLGD must have an
`atlas:promotedFrom` link pointing to its source in the LGD.

**Why a regulator cares:** Without provenance, you cannot trace a decision back
to its source data. If a customer was contacted based on a wealth signal, the
regulator needs to see the chain: which source system produced the data, when
was it promoted, and by what process.

**What a violation looks like:** A Customer node exists in the SLGD with no
`promotedFrom` property. This means data entered the authoritative graph without
going through the governed promotion path.

**How to fix:** Ensure all data enters the SLGD via the Module 5 promotion
script, which automatically attaches provenance.

---

## Shape 2: BoundaryShape

**What it constrains:** Every Score node must be marked `atlas:probabilistic = true`
and must carry an `atlas:confidence` value between 0 and 1.

**Why a regulator cares:** Scores are produced by machine learning models (XGBoost).
Without explicit marking, a probabilistic output could silently enter a
deterministic decision path. The boundary between deterministic and probabilistic
components is the core architectural commitment of ATLAS — SR 11-7 and OCC 2011-12
require that models used in consequential decisions be reproducible and subject to
independent validation.

**What a violation looks like:** A Score node exists without `probabilistic = true`
or without a confidence value. This means an ML output is unmarked — a reviewer
cannot distinguish it from a deterministic calculation.

**How to fix:** Ensure the scoring pipeline always attaches `probabilistic = true`
and `confidence` to every Score instance.

---

## Shape 3: ComplianceInputShape

**What it constrains:** Every Score node must have `atlas:explainability = true`
and `atlas:modelVersion` (a string identifying the model that produced it).

**Why a regulator cares:** A score used as a compliance input must be explainable
(SHAP attributions must accompany it) and version-pinned (so the same score can
be reproduced by running the same model version against the same inputs).

**What a violation looks like:** A Score exists without SHAP attributions or
without a model version identifier. This means the score cannot be independently
validated or reproduced.

**How to fix:** Ensure the SageMaker XGBoost endpoint always returns SHAP values
alongside the score, and that the model version is recorded.

---

## Shape 4: RoutingPolicyShape

**What it constrains:** Every RoutingDecision must select exactly one route from
the closed set: ROUTE_ADVISOR_QUEUE, ROUTE_SUPPRESSION_LIST, or ROUTE_ESCALATION.

**Why a regulator cares:** The routing decision determines what action is taken
on a customer. If an LLM could invent arbitrary routes outside the enumerated set,
the system's behavior would be unpredictable and unauditable. The closed set
ensures every possible action is known in advance and can be reviewed.

**What a violation looks like:** A RoutingDecision has a `selectedRoute` value
that is not one of the three permitted values — for example, an LLM-generated
string like "ROUTE_DIRECT_CONTACT" that was never defined in the state machine.

**How to fix:** Ensure the bounded agent (Step Functions state machine) only
produces routes from the declared set. The SHACL shape is the backstop that
catches any violation that slips through.

---

## Shape 5: WealthSignalTypeShape

**What it constrains:** Every WealthSignal must have exactly one signal type
from the SKOS WealthSignalTypeScheme.

**Why a regulator cares:** Signal classification determines downstream treatment.
A signal without a type cannot be routed correctly. A signal with multiple types
creates ambiguity in the audit trail.

**What a violation looks like:** A WealthSignal exists with zero or more than one
`hasSignalType` value.

**How to fix:** Ensure the signal-derivation logic (Module 5/7) always assigns
exactly one type from the closed SKOS scheme.

---

## Shape 6: CoverageRelationshipShape

**What it constrains:** Every AdvisoryRelationship must have:
- Exactly one `coverageStartDate` (xsd:date)
- At most one `coverageEndDate` (xsd:date)
- Exactly one `relationshipType` from the RelationshipTypeScheme
- Exactly one `coveringAdvisor` (must be an Advisor)
- Exactly one `advisesCustomer` (must be a Customer)

**Why a regulator cares:** Advisory coverage determines who is responsible for a
customer's wealth management relationship. Incomplete or ambiguous coverage records
create accountability gaps — if a customer is contacted without a valid coverage
assignment, the institution cannot demonstrate that the contact was authorized.

**What a violation looks like:** An AdvisoryRelationship exists without a start
date, without a covering advisor, or with multiple conflicting relationship types.

**How to fix:** Ensure the Module 8 workflow (for new assignments) and the legacy
data migration (for existing assignments) both produce complete AdvisoryRelationship
instances with all required fields.

---

## Running the validator in CI

The SHACL validator runs in CI on every pull request. The workflow is at
`.github/workflows/end-to-end.yml`. A failing shape blocks the merge.

The validator also runs as part of the Module 5 promotion path — data that
violates any shape is not promoted from the LGD to the SLGD.
