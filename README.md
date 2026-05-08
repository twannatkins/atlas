# ATLAS — Aligned Three-Layer Architecture for Semantics

An open-source Financial Services Industry (FSI) semantic layer reference architecture
and Amazon SageMaker notebook workshop on AWS.

**Lead use case:** Identifying wealth signals from inside the bank.
**Audience:** FSI architects and ontologists who need to build and defend a
knowledge graph to a Model Risk Management (MRM) reviewer.

---

## What ATLAS Is

ATLAS demonstrates how to build an AWS-native enterprise semantic layer for FSI
institutions. It implements a three-layer pattern — data integration, ontology
and digital twin, and application — bound to the Financial Industry Business
Ontology (FIBO) as its alignment vocabulary.

The architecture's central commitment is the **deterministic-vs-probabilistic
boundary**: every component is classified, the boundary is enforced by Shapes
Constraint Language (SHACL) shapes, and the shapes are runnable artifacts in
this repository. A Model Risk Management reviewer can run one validator and
produce a report showing exactly where probabilistic outputs entered the system
and exactly which deterministic constraints prevent them from corrupting
compliance-bound paths.

ATLAS is not a productized platform. It is a reference pattern with runnable code.

---

## Architecture in 30 Seconds

```
┌─────────────────────────────────────────────────────────────────┐
│  Application Layer                                              │
│  Bedrock (NL↔SPARQL only) · Step Functions agent · AppSync UI  │
├─────────────────────────────────────────────────────────────────┤
│  Ontology and Digital Twin Layer                                │
│  LGD (raw, unvalidated)  →  SLGD (FIBO-aligned, SHACL-valid)  │
│  Amazon Neptune two-tier · SHACL boundary enforcement           │
├─────────────────────────────────────────────────────────────────┤
│  Data Integration Layer                                         │
│  Pattern A: S3 Iceberg → Ontop → R2RML                          │
│  Pattern B: Snowflake Horizon (or Athena fallback) → Ontop      │
│  Pattern C: Kinesis/MSK → Lambda → LGD                          │
└─────────────────────────────────────────────────────────────────┘
```

LGD = Lexical Graph Database (fast, lossy, not authoritative).
SLGD = Semantic Layer Graph Database (curated, validated, authoritative).

---

## Eight-Module Table of Contents

| # | Module | Runtime |
|---|--------|---------|
| 1 | [From Business Question to Ontology](notebooks/01_journey_to_ontology.ipynb) | 30–45 min |
| 2 | [FIBO Alignment and the Extension Ring](notebooks/02_fibo_alignment.ipynb) | 60–75 min |
| 3 | Standing Up Two-Tier Neptune | 30–45 min |
| 4 | Three Patterns for Source Connection | 45–60 min |
| 5 | Entity Resolution and the Promotion Path | 30–45 min |
| 6 | SHACL: Making the Boundary Mechanical | 45–60 min |
| 7 | Bedrock at the Edges | 30–45 min |
| 8 | The Wealth-Signal Demo with Bounded Agent | 45–60 min |

Total: approximately 5–6 hours of focused work.

---

## Workshop Guide

The step-by-step guide lives in [workshop/content/](workshop/content/) and renders
as an AWS Workshop Studio site. Begin with Module 1 at
[workshop/content/01-from-business-question/index.md](workshop/content/01-from-business-question/index.md).

---

## Cost to Run

A single architect completing the full workshop end-to-end (approximately five to
six hours of active infrastructure time) should expect **$10–$18 in us-east-1**,
dominated by two Neptune clusters and Bedrock invocations in Module 7. Run the
cleanup notebook at the end of your session — the two Neptune clusters cost
approximately $17 per day combined if left running.

A full cost breakdown will be added before the workshop's public release.

---

## Prerequisites

- An AWS account with SageMaker notebook permissions and Bedrock model access
  enabled in us-east-1
- No prior ontology experience required for Module 1
- Subsequent modules assume you have completed prior modules

---

## Synthetic Data

All data in this workshop is synthetic, generated with a fixed random seed.
No real customer data is used anywhere. Generators are in
[notebooks/shared/atlas_synthetic.py](notebooks/shared/atlas_synthetic.py).

---

## Mapping This to Your Industry

The wealth-signal use case is the vehicle; the architecture is the product.
Architectural commentary in every module is industry-neutral.

- **Insurance:** replace wealth-signal taxonomy with claim-pattern-to-product-fit signals
- **Asset management:** replace with family-office relationship surface signals
- **Capital markets:** replace with counterparty-to-product fit signals

---

## License

MIT-0. See [LICENSE](LICENSE).

FIBO is published under the MIT license by the Enterprise Data Management Council (EDM Council).
The version of FIBO pinned in this workshop is cited in [ontology/README.md](ontology/README.md).

---

## Contributing

Contribution guidelines and security policy will be added before the public release.
