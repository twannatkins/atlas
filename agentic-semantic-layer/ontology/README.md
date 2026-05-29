# Ontology — the heart of the agentic semantic layer

This directory contains the **FIBO-aligned ontology** that defines what concepts and relationships exist in the bank's knowledge graph. Every triple stored in Neptune conforms to a class defined here. Every SPARQL query an agent issues in Workshop 2 is written against the vocabulary defined here. Every SHACL boundary shape that protects the deterministic layer references the classes defined here.

The ontology is not configuration. It is the *contract* between data engineering, application development, and compliance — written in a form (OWL and RDF) that both machines and standards bodies recognize.

## What's in this directory

```
ontology/
├── atlas-core.ttl                # 19 classes that define the bank's domain
├── atlas-fibo-alignment.ttl      # 3 classes that bridge atlas: to FIBO
├── atlas-shapes.ttl              # 6 SHACL boundary shapes
├── extensions/
│   ├── dcat-bindings.ttl         # Data catalog vocabulary alignment
│   ├── gleif-bindings.ttl        # Legal entity identifier alignment
│   ├── prov-o-bindings.ttl       # Provenance vocabulary alignment
│   └── skos-codelists.ttl        # SKOS concept schemes (signal types, routing decisions, etc.)
├── alignment-gaps.md             # Where FIBO doesn't cover what the bank needs, and how atlas: closes the gap
├── rationale.md                  # Design decisions and the reasoning behind them
└── README.md                     # This file
```

## The 24 classes

The ontology declares 24 classes across the `atlas:` namespace:

**Core domain (19 classes in `atlas-core.ttl`):** Customer, Account, Holding, Transaction, Household, WealthSignal, Eligibility, Score, RoutingDecision, HumanReview, AuditRecord, Advisor, WorkflowStep, WealthSignalType, HouseholdMembership, DataSource, ObservationWindow, PreviousSurfacing, AdvisoryRelationship.

**FIBO alignment bridges (3 classes in `atlas-fibo-alignment.ttl`):** LegalEntity, Product, LineOfBusiness.

**Governance extensions (2 classes in `extensions/prov-o-bindings.ttl`):** PromotionActivity, EntityResolutionActivity.

Each class is documented in the TTL files with `rdfs:label`, `rdfs:comment`, and where applicable an `owl:equivalentClass` or `rdfs:subClassOf` link to its FIBO counterpart. The mapping between `atlas:` classes and FIBO classes is the substance of `atlas-fibo-alignment.ttl`.

## The 6 SHACL shapes

The shapes in `atlas-shapes.ttl` are the deterministic boundary — the rules that decide what is allowed to enter the graph. They are the most important artifact in this directory from a model risk perspective:

| Shape | What it asserts |
|---|---|
| `atlas:ProvenanceShape` | Every promoted entity in the SLGD has full PROV-O attribution back to its source |
| `atlas:BoundaryShape` | Every probabilistic output (Bedrock-drafted narrative, ML score) carries the required confidence and review flags |
| `atlas:ComplianceInputShape` | Every compliance-bound path carries the explainability artifacts required by SR 11-7 and OCC 2011-12 |
| `atlas:RoutingPolicyShape` | Every routing decision is drawn from the closed enumerated set defined in the SKOS scheme |
| `atlas:WealthSignalTypeShape` | Every wealth signal type is drawn from the SKOS scheme — this is what makes new signals additive rather than ad hoc |
| `atlas:CoverageRelationshipShape` | Every advisory relationship has the required client, advisor, effective date, and line-of-business properties |

These shapes are what makes the ontology *governable*. Without them, the graph is just a graph. With them, the graph is a regulated artifact.

## How agents use the ontology (Workshop 2 preview)

In Workshop 2, registered agents consume this ontology in five ways:

1. **SPARQL queries** are written against the class names defined here
2. **GraphQL fragments** are shaped to the class hierarchy defined here
3. **SHACL validation** runs against the shapes defined here before any new triple is accepted
4. **Provenance traces** in the UI follow the PROV-O bindings defined in `extensions/prov-o-bindings.ttl`
5. **SKOS code lists** in `extensions/skos-codelists.ttl` populate dropdowns and enumerated choices in the UI

Workshop 2 does **not** modify any file in this directory. Workshop 2 extensions to the vocabulary live in `../use-case-applications/ontology-extensions/` under the `atlas-part-2:` namespace. This isolation is intentional — Workshop 1's ontology is a stable artifact that downstream workshops and customer deployments can rely on.

## Where to start reading

- New to ontology engineering? Start with `rationale.md` — the design decisions in plain English.
- New to FIBO? Read `alignment-gaps.md` — what FIBO covers, what it doesn't, and why.
- Ready to read code? Start with `atlas-core.ttl` and walk through the 19 classes. Then `atlas-fibo-alignment.ttl` for the FIBO bridge, then `atlas-shapes.ttl` for the deterministic boundary.

The eight teaching notebooks in `../notebooks/` walk through all of the above in order, with executable examples. If you are working through the workshop, follow the notebooks rather than reading the TTL files directly.
