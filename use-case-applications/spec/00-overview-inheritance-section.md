# Replacement section for 00-overview.md

This replaces the existing "What Part 2 inherits from Part 1" section in `use-case-applications/spec/00-overview.md`. The original text contained several factual inaccuracies about Workshop 1's artifacts; this version is verified against the actual Workshop 1 repository contents.

---

## What Workshop 2 inherits from Workshop 1

Workshop 2 is downstream of Workshop 1 (`agentic-semantic-layer/`) and reuses everything Workshop 1 ships. The full, authoritative contract is in `03-data-contracts.md`. This section is a high-level summary.

| Workshop 1 artifact | How Workshop 2 uses it |
|---|---|
| **22 ontology classes** (19 in `atlas-core.ttl` + 3 introduced by FIBO alignment in `atlas-fibo-alignment.ttl`) | The vocabulary all GraphQL fragments and SPARQL queries are written against |
| **FIBO/GLEIF/DCAT/SKOS/PROV-O bindings** (in `agentic-semantic-layer/ontology/extensions/`) | The semantic alignment that makes the schema legible to FSI standards bodies |
| **6 SHACL shapes** in `atlas-shapes.ttl`: `ProvenanceShape`, `BoundaryShape`, `ComplianceInputShape`, `RoutingPolicyShape`, `WealthSignalTypeShape`, `CoverageRelationshipShape` | The deterministic boundary that separates rule-based logic from probabilistic agents |
| **3 R2RML mappings** across three connection patterns (Pattern A — Iceberg ×2, Pattern B — Snowflake Horizon ×1) plus a Pattern C real-time event handler | The federated read path the GraphQL resolvers depend on |
| **Synthetic data**: 200 customers, 3,747 transactions, 10 advisors, 105 advisory relationships | The data the workshop runs against; replaceable via the substitution guide |
| `agentic-semantic-layer/prompts/ground-truth.yaml` (NL→SPARQL pairs) | Test cases for the `nl-to-sparql-agent`; used in verification cells |
| `agentic-semantic-layer/prompts/prefixes.txt` | The canonical SPARQL prefix preamble all Workshop 2 agents use |
| `agentic-semantic-layer/prompts/tips.yaml` | Additional NL→SPARQL prompt guidance |
| `agentic-semantic-layer/docs/model-risk-review.md` | Inherited as-is for MRM submission; Workshop 2 does not re-litigate the shapes |
| `agentic-semantic-layer/docs/runbook.md` | CIO-level demo runbook; Workshop 2 extends but does not modify |
| `agentic-semantic-layer/notebooks/shared/*.py` | Neptune, SPARQL, synthetic data, and validator helpers reused by Workshop 2 notebooks |
| `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` | The two-tier Neptune (LGD + SLGD) CFN template; Workshop 2 expects a cluster deployed from this template to be standing with the SLGD populated |
| Workshop 1 notebooks (8 modules, `01_journey_to_ontology.ipynb` through `08_wealth_signal_demo.ipynb`) | Reference material; Workshop 2 does not modify them |

Workshop 2 does not modify Workshop 1. Any extension to the ontology that Workshop 2 needs is recorded in `03-data-contracts.md` as a Workshop 2-only addition, isolated in the `atlas-part-2:` namespace under `use-case-applications/ontology-extensions/` so Workshop 1 remains a stable artifact.

### Specific Workshop 2 extensions to the vocabulary

Workshop 2 introduces four new classes and five new SKOS concepts in the `atlas-part-2:` namespace. None of these modify Workshop 1's files. The full list is in `03-data-contracts.md`. Briefly:

- `atlas-part-2:Referral` — the business-facing noun for the routing event; carries an `atlas:RoutingDecision`
- `atlas-part-2:Session` — clickstream-derived session for Engagement Decay signals (Phase 2)
- `atlas-part-2:NetworkContact` — cross-LOB connection for Network Influence signals (Phase 2)
- `atlas-part-2:ThemeAssertion` — market/portfolio themes for the Wealth UI Themes route (Phase 2)

Five new SKOS concepts are added to Workshop 1's existing `atlas:WealthSignalType` concept scheme, representing the named signals surfaced in the UI: `LargeInboundWireSignal`, `SegmentShiftSignal`, `NoAdvisorCoverageSignal`, `EngagementDecaySignal`, `NetworkInfluenceSignal`. All five are validated by Workshop 1's existing `atlas:WealthSignalTypeShape` — Workshop 2 introduces no new SHACL shapes.
