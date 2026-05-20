# 03 — Data Contracts

The contract between Workshop 1 (`agentic-semantic-layer/`) and Workshop 2 (`use-case-applications/`).

This document is the source of truth for what Workshop 2 expects to find in your Workshop 1 environment, and for any Workshop 2-only extensions to the vocabulary. Every assertion in this document is verified by the pre-flight notebook before Workshop 2 is allowed to start.

If you change anything in Workshop 1's `ontology/`, `mappings/`, or `data/synthetic/` directories, this document is the first place to update.

## What Workshop 2 inherits from Workshop 1

### Ontology classes (22 total)

Workshop 1's ontology defines 22 classes across two files. Workshop 2 references these classes by their canonical local names; do not rename them.

**Defined in `agentic-semantic-layer/ontology/atlas-core.ttl` (19 classes):**

| Class | Role in Workshop 2 |
|---|---|
| `atlas:Customer` | Primary identity for Consumer Banking and Wealth personas |
| `atlas:Account` | Federated from Iceberg via Pattern A mapping |
| `atlas:Holding` | Portfolio positions surfaced in Wealth UI Client 360 |
| `atlas:Transaction` | Federated from Snowflake Horizon via Pattern B mapping |
| `atlas:Household` | Surface for Wholesale UI relationship strip |
| `atlas:WealthSignal` | Carrier for wealth-readiness signals on Wholesale UI |
| `atlas:Eligibility` | Wealth-eligible state tracking |
| `atlas:Score` | SHAP-explainable risk and fit scores |
| `atlas:RoutingDecision` | Underlying noun for `atlas-part-2:Referral` (see extensions) |
| `atlas:HumanReview` | Human-in-the-loop attestation for SAR drafts and rationale approval |
| `atlas:AuditRecord` | PROV-O audit trail surface in both UIs |
| `atlas:Advisor` | Wealth UI primary persona; targets for referral routing |
| `atlas:WorkflowStep` | Step Functions step representation in the graph |
| `atlas:WealthSignalType` | SKOS-scheme-bound signal type values |
| `atlas:HouseholdMembership` | Membership edges for household traversal |
| `atlas:DataSource` | Provenance attribution to source system |
| `atlas:ObservationWindow` | Time-bounded behavioral signal scope |
| `atlas:PreviousSurfacing` | Prevents duplicate referrals for the same signal |
| `atlas:AdvisoryRelationship` | The advisor-to-client coverage relationship |

**Defined in `agentic-semantic-layer/ontology/atlas-fibo-alignment.ttl` (3 classes):**

| Class | Role in Workshop 2 |
|---|---|
| `atlas:LegalEntity` | Corporate party representation; FIBO-aligned |
| `atlas:Product` | Product offerings; basis for product affinity scoring |
| `atlas:LineOfBusiness` | LOB scoping for network influence signals |

### SHACL shapes (6 total)

Workshop 1 defines six SHACL NodeShapes in `agentic-semantic-layer/ontology/atlas-shapes.ttl`. Workshop 2 does not add new shapes — all Workshop 2 signal logic is expressed as SPARQL CONSTRUCT queries that produce instances of existing classes (`atlas:WealthSignal`, `atlas:WealthSignalType`) which are then validated by the existing shapes.

| Shape | What Workshop 2 uses it for |
|---|---|
| `atlas:ProvenanceShape` | Asserts every wealth signal surfaced in the UI carries PROV-O attribution back to the SHACL shape that fired and the R2RML mapping that produced the underlying triple |
| `atlas:BoundaryShape` | Asserts every Bedrock-drafted referral rationale carries the required probabilistic-output flags before being shown to the user |
| `atlas:ComplianceInputShape` | Asserts every compliance-bound decision (referral routing, SAR draft) carries the explainability artifacts required by SR 11-7 / OCC 2011-12 |
| `atlas:RoutingPolicyShape` | Asserts every routing decision is from the closed enumerated set (route to advisor, hold for review, decline) |
| `atlas:WealthSignalTypeShape` | Asserts wealth signal types are drawn from the SKOS concept scheme — this is the shape that fires for `LargeInboundWire`, `SegmentShift`, `NoAdvisorCoverage`, `EngagementDecay`, and `NetworkInfluence` signal types |
| `atlas:CoverageRelationshipShape` | Asserts every `atlas:AdvisoryRelationship` has the required properties (client, advisor, effective date, line of business) |

**Note on naming.** Earlier drafts of the Workshop 2 spec referenced `LargeInboundWireShape`, `SegmentShiftShape`, and `EngagementDecayShape` as if each named signal warranted its own SHACL shape. This was incorrect. In Workshop 1's architecture, signal *types* are SKOS concepts validated by the single `atlas:WealthSignalTypeShape`. The specific logic that fires each signal lives in SPARQL CONSTRUCT queries owned by the `wealth-signal-detector` agent, not in dedicated shapes. This keeps the shape count bounded as new signals are added.

### R2RML mappings and connection patterns

Workshop 1 ships three R2RML mappings across three connection patterns, plus a real-time event handler. Workshop 2's AppSync resolvers federate against these.

| Pattern | Source | Mapping | Workshop 2 use |
|---|---|---|---|
| Pattern A — Iceberg | Lake Formation Iceberg tables | `mappings/pattern_a_iceberg/customer-master.r2rml.ttl` | Primary read path for Customer, Household, Account entities |
| Pattern A — Iceberg | Lake Formation Iceberg tables | `mappings/pattern_a_iceberg/advisory-relationships.r2rml.ttl` | Read path for advisor coverage |
| Pattern B — Snowflake Horizon | Snowflake | `mappings/pattern_b_snowflake_horizon/transaction-history.r2rml.ttl` | Transaction federation for behavioral signal SPARQL queries |
| Pattern C — Real-time | Kinesis events | `mappings/pattern_c_realtime/event-to-lgd.py` | Phase 2 only — feeds AgentCore Memory's session context |

Workshop 2's `atlas-sparql-mcp` queries through these mappings transparently via Ontop. The Ontop service is **not** deployed by Workshop 1 — Workshop 2's CDK stack (`use-case-applications/cdk/`) deploys Ontop on ECS Fargate as part of the workshop infrastructure. See `02-prerequisites.md`.

### Synthetic data

Workshop 1's synthetic data is the corpus Workshop 2 runs against. The substitution guide (`09-substitution-guide.md`) explains how to swap this for real Gold-tier data.

| File | Records | Workshop 2 use |
|---|---|---|
| `agentic-semantic-layer/data/synthetic/customer-master.json` | 200 | Customer corpus for both UIs |
| `agentic-semantic-layer/data/synthetic/transaction-history.json` | 3,747 | Transaction corpus for wealth signals and behavioral analysis |
| `agentic-semantic-layer/data/synthetic/advisors.json` | 10 | Wealth Advisor corpus; routing targets for the referral orchestrator |
| `agentic-semantic-layer/data/synthetic/advisory-relationships.json` | 105 | Advisor-to-client coverage; basis for "no advisor coverage" gap signals |

For the Rachel Kim demo scenario in Phase 1, the seeded customer Anjali Patel (`atlas:cust/9c2a1e` in the household `atlas:hh/9c2a1e`) is the canonical example. The demo scenario assumes this seed; if the synthetic data generator is re-run with a different random seed, update the Rachel Kim narrative in `06-react-monorepo/wholesale-app/routes/referrals/detail-spec.md`.

### Files Workshop 2 reads from Workshop 1

Workshop 2's notebooks and agents directly read these Workshop 1 artifacts:

| Path | Used by |
|---|---|
| `agentic-semantic-layer/prompts/prefixes.txt` | Canonical SPARQL prefix preamble for every Workshop 2 agent |
| `agentic-semantic-layer/prompts/ground-truth.yaml` | Test corpus for `nl-to-sparql-agent` verification cells |
| `agentic-semantic-layer/prompts/tips.yaml` | Additional NL→SPARQL prompt guidance |
| `agentic-semantic-layer/docs/model-risk-review.md` | Inherited as-is for MRM submission; Workshop 2 does not re-litigate |
| `agentic-semantic-layer/docs/runbook.md` | CIO-level demo runbook; Workshop 2 extends but does not modify |
| `agentic-semantic-layer/notebooks/shared/atlas_neptune.py` | Neptune connection helpers reused by Workshop 2 notebooks |
| `agentic-semantic-layer/notebooks/shared/atlas_sparql.py` | SPARQL client, URI sanitization, and query validation reused by Workshop 2 notebooks and resolvers |
| `agentic-semantic-layer/notebooks/shared/atlas_synthetic.py` | Synthetic data utilities for substitution-guide testing |
| `agentic-semantic-layer/notebooks/shared/atlas_validators.py` | SHACL validation helpers |
| `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` | The Neptune CFN template; Workshop 2 expects a cluster deployed from this template to be standing with the SLGD populated |

## What Workshop 2 adds (the `atlas-part-2:` namespace)

Workshop 2 introduces new classes only when no Workshop 1 class fits. All Workshop 2-introduced classes use the `atlas-part-2:` namespace and live in `use-case-applications/ontology-extensions/`. Workshop 1's ontology files are never modified.

### New classes

| Class | Defined in | Rationale |
|---|---|---|
| `atlas-part-2:Referral` | `use-case-applications/ontology-extensions/referrals.ttl` | The business-facing noun for a wealth-eligible customer being routed to an advisor. Distinct from `atlas:RoutingDecision`, which models the *act* of routing. A `Referral` has a `RoutingDecision`. |
| `atlas-part-2:Session` | `use-case-applications/ontology-extensions/behavioral.ttl` | A user interaction session derived from clickstream. Basis for Engagement Decay signals. |
| `atlas-part-2:NetworkContact` | `use-case-applications/ontology-extensions/behavioral.ttl` | A cross-LOB connection between a household member and a non-wealth banker. Basis for Network Influence signals. |
| `atlas-part-2:ThemeAssertion` | `use-case-applications/ontology-extensions/themes.ttl` | A market or portfolio theme connected to a holding or client. Used by the Wealth UI Themes route. |

### New SKOS concepts (added to existing schemes)

The five named wealth signal types referenced in the UI mockups become new SKOS concepts within Workshop 1's existing `atlas:WealthSignalType` scheme. They are added as a Workshop 2 extension in `use-case-applications/ontology-extensions/signal-types.ttl`:

| Concept | Fired by |
|---|---|
| `atlas-part-2:LargeInboundWireSignal` | `wealth-signal-detector` SPARQL CONSTRUCT over transactions |
| `atlas-part-2:SegmentShiftSignal` | `wealth-signal-detector` SPARQL CONSTRUCT over transaction velocity |
| `atlas-part-2:NoAdvisorCoverageSignal` | `wealth-signal-detector` SPARQL CONSTRUCT over `atlas:AdvisoryRelationship` absence |
| `atlas-part-2:EngagementDecaySignal` | `behavioral-signal-agent` SPARQL CONSTRUCT over `atlas-part-2:Session` (Phase 2) |
| `atlas-part-2:NetworkInfluenceSignal` | `behavioral-signal-agent` SPARQL CONSTRUCT over `atlas-part-2:NetworkContact` (Phase 2) |

Each signal type is validated by Workshop 1's existing `atlas:WealthSignalTypeShape`. No new SHACL shapes are introduced.

### No modifications to Workshop 1 SHACL shapes

Workshop 2 does not modify the six SHACL shapes in `agentic-semantic-layer/ontology/atlas-shapes.ttl`. If a Workshop 2 use case requires a new shape, the shape is added to `use-case-applications/ontology-extensions/shapes.ttl` with the `atlas-part-2:` prefix. As of this writing, no such shape is needed.

## Pre-flight verification

The pre-flight notebook (`use-case-applications/notebooks/phase-1-referral/00_preflight.ipynb`) verifies every assertion in this document before Workshop 2 is allowed to start. Specifically:

```python
# Class count assertion
assert len(query_classes_in_namespace("atlas:")) == 22, \
    "Workshop 1 ontology must declare 22 classes in the atlas: namespace"

# Specific class existence assertions
required_classes = [
    "atlas:Customer", "atlas:Account", "atlas:Holding", "atlas:Transaction",
    "atlas:Household", "atlas:WealthSignal", "atlas:WealthSignalType",
    "atlas:Advisor", "atlas:AdvisoryRelationship", "atlas:RoutingDecision",
    "atlas:HumanReview", "atlas:AuditRecord", "atlas:LegalEntity",
    "atlas:Product", "atlas:LineOfBusiness",
]
for cls in required_classes:
    assert class_exists_in_graph(cls), f"Required Workshop 1 class missing: {cls}"

# SHACL shape assertion
required_shapes = [
    "atlas:ProvenanceShape", "atlas:BoundaryShape", "atlas:ComplianceInputShape",
    "atlas:RoutingPolicyShape", "atlas:WealthSignalTypeShape",
    "atlas:CoverageRelationshipShape",
]
for shape in required_shapes:
    assert shape_exists_in_graph(shape), f"Required Workshop 1 shape missing: {shape}"

# Data count assertions
assert count_instances("atlas:Customer") == 200, "Expected 200 customers"
assert count_instances("atlas:Transaction") == 3747, "Expected 3,747 transactions"
assert count_instances("atlas:Advisor") == 10, "Expected 10 advisors"
assert count_instances("atlas:AdvisoryRelationship") == 105, \
    "Expected 105 advisory relationships"

# File existence assertions
required_files = [
    "agentic-semantic-layer/prompts/prefixes.txt",
    "agentic-semantic-layer/prompts/ground-truth.yaml",
    "agentic-semantic-layer/notebooks/shared/atlas_neptune.py",
    "agentic-semantic-layer/notebooks/shared/atlas_sparql.py",
]
for path in required_files:
    assert file_exists(path), f"Required Workshop 1 file missing: {path}"
```

If any of these assertions fail, the pre-flight notebook halts and surfaces diagnostic remediation guidance. Workshop 2 cannot proceed until Workshop 1 is in a known-good state.

## When Workshop 1 changes

If Workshop 1 adds a new ontology class, a new SHACL shape, or changes the synthetic data row counts, this document is updated in the same commit. Workshop 2's pre-flight assertions are regenerated from this document — they should never diverge.

The substitution guide (`09-substitution-guide.md`) explains how to swap synthetic data for real Gold-tier data without modifying any of the contracts above. Real data substitution is a configuration change, not an ontology or shape change.
