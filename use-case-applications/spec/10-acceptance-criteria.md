# 10 — Acceptance Criteria

Phase 1 acceptance assertions. Every assertion in this document is verified by `07_phase_1_acceptance.ipynb`. If all pass, Phase 1 is complete and ready for customer handoff. If any fail, the failure must be resolved before extending to Phase 2.

## Category 1 — Registry completeness

| # | Assertion | What it proves |
|---|---|---|
| 1.1 | 5 MCP servers are registered and discoverable | The capability surface is complete |
| 1.2 | 5 Phase 1 agents are registered and discoverable | The agent layer is complete |
| 1.3 | Consumer Banker discovers at least 4 agents | Persona-scoped discovery works for the primary persona |
| 1.4 | Wealth Advisor discovers a different set than Consumer Banker | Discovery is persona-scoped, not universal |
| 1.5 | `referral-rationale-drafter` is NOT discoverable by Wealth Advisor | The most sensitive agent is correctly restricted |
| 1.6 | `referral-orchestrator` is discoverable ONLY by Consumer Banker | Workflow agents are persona-locked |

## Category 2 — Agent posture compliance

| # | Assertion | What it proves |
|---|---|---|
| 2.1 | `nl-to-sparql-agent` produces identical SPARQL for the same question across 5 runs | Determinism holds |
| 2.2 | `nl-to-sparql-agent` does NOT call any Bedrock text-generation model | LLM-at-the-edges: no free SPARQL generation |
| 2.3 | `wealth-signal-detector` validates all output via SHACL before write | SHACL-driven posture holds |
| 2.4 | `referral-rationale-drafter` output always carries `is_probabilistic: true` | Probabilistic flag is hardcoded |
| 2.5 | `referral-rationale-drafter` output always carries `requires_human_review: true` | Human-in-the-loop flag is hardcoded |
| 2.6 | `referral-orchestrator` rejects invocations without `approved_rationale` | No auto-routing without human approval |
| 2.7 | `referral-orchestrator` rejects non-`atlas-consumer-banker` persona claims | Persona restriction enforced |

## Category 3 — Four-layer permission model

| # | Assertion | What it proves |
|---|---|---|
| 3.1 | Identity layer: persona claim is present on every MCP server invocation | No anonymous queries |
| 3.2 | Application layer: Consumer Banker and Wealth Advisor see different capability palettes | Cognito group scoping works |
| 3.3 | Data layer: Consumer Banker query returns fewer customers than BSA Analyst | Lake Formation row filtering works |
| 3.4 | Semantic layer: Consumer Banker cannot traverse to BSA-restricted named graphs | SHACL named graph scoping works |

## Category 4 — Regulatory compliance

| # | Assertion | What it proves |
|---|---|---|
| 4.1 | Compliance banner for non-BSA personas does NOT contain "SAR" | Tipping-off prohibition (31 U.S.C. §5318(g)(2)) |
| 4.2 | Compliance banner for non-BSA personas does NOT contain "filed" | Tipping-off prohibition |
| 4.3 | BSA Analyst CAN see SAR-specific detail in the banner | BSA function has appropriate access |
| 4.4 | No probabilistic agent output is committed to the graph without human approval | SR 11-7 / OCC 2011-12 compliance |

## Category 5 — End-to-end Rachel Kim scenario

| # | Assertion | What it proves |
|---|---|---|
| 5.1 | Patel household (`atlas:hh/9c2a1e`) exists in the SLGD | Synthetic data is loaded |
| 5.2 | `wealth-signal-detector` detects at least one signal for the Patel household | Signal detection works end-to-end |
| 5.3 | `household-traverser` returns at least 2 nodes for the Patel household | Graph traversal works |
| 5.4 | `referral-rationale-drafter` produces a non-empty draft for the Patel household | Narrative generation works |
| 5.5 | `referral-orchestrator` routes successfully with an approved rationale | Full workflow completes |
| 5.6 | An `atlas:AuditRecord` exists after the routing workflow completes | Audit trail is written |
| 5.7 | The audit record carries PROV-O attribution (`prov:wasGeneratedBy`, `prov:generatedAtTime`) | Provenance is complete |

## Category 6 — GraphQL schema conformance

| # | Assertion | What it proves |
|---|---|---|
| 6.1 | Every entity type in the schema maps to an ontology class | FIBO-shaped contract holds |
| 6.2 | Customer query returns `uri`, `customerId` (required fields) | Schema contract is honored |
| 6.3 | WealthSignal query returns `signalType`, `strength` | Signal schema is correct |
| 6.4 | Capability query returns persona-filtered results | Registry integration works |

## Category 7 — Workshop 1 substrate integrity

| # | Assertion | What it proves |
|---|---|---|
| 7.1 | No files in `agentic-semantic-layer/` were modified by this branch | Workshop 1 is untouched |
| 7.2 | Workshop 1's 22 ontology classes still exist | Ontology integrity |
| 7.3 | Workshop 1's 6 SHACL shapes still exist | Shape integrity |
| 7.4 | Workshop 2 extensions use `atlas-part-2:` namespace exclusively | Namespace isolation |

## Passing criteria

All assertions in Categories 1–4 and 6–7 must pass. Category 5 (end-to-end scenario) requires a running Neptune cluster with synthetic data loaded — if the cluster is not available, Category 5 assertions are marked as "deferred to deployment" rather than "failed."
