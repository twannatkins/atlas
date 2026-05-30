---
title: "Module 7 — Phase 1 Acceptance"
weight: 70
---

# Module 7 — Phase 1 Acceptance

## Learning Objectives

- Run the full Phase 1 acceptance suite and interpret each category of assertions
- Distinguish between assertions that run locally (registry, posture, regulatory,
  schema) and assertions that require a live Neptune cluster (end-to-end scenario)
- Understand what "deferred to deployment" means — and why it is not the same as
  a failure
- Confirm that every architectural commitment made in Modules 2–6 is verifiable
  at the assertion level

## Time Estimate

20–30 minutes. Allow extra time if any local assertion fails and requires debugging.

## Prerequisites

- All of Modules 2–6 complete
- All module-level verification cells passing

## What You Will Build

Nothing new. This notebook runs the formal acceptance suite from
`spec/10-acceptance-criteria.md` against everything you built in Phase 1. The
suite is organized into 36 assertions across seven categories. Read cell 1
(`cell-01-concept`) before running any code — it frames what each category proves:

1. **Registry completeness** — all agents and MCP servers are registered and discoverable
2. **Agent posture compliance** — each agent honors its declared posture (deterministic-audited, SHACL-validated, or probabilistic)
3. **Four-layer permission model** — identity, application, data, and semantic layers all compose correctly
4. **Regulatory compliance** — tipping-off prohibition is mechanically enforced, probabilistic outputs are flagged
5. **End-to-end scenario** — the Rachel Kim referral workflow completes end-to-end (requires live Neptune)
6. **GraphQL schema conformance** — every entity type maps to an ontology class
7. **Workshop 1 substrate integrity** — no Workshop 1 files were modified by Workshop 2

Categories 1–4 and 6–7 run locally. Category 5 requires a live Neptune cluster
and is deferred if the cluster is not reachable.

The notebook is `notebooks/phase-1-referral/06_phase_1_acceptance.ipynb`.

## Steps

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/06_phase_1_acceptance.ipynb` in SageMaker
Studio. Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 1)

Read cell 1 (`cell-01-concept`) for the full list of assertions by category and
what each one proves.

### Step 3 — Run setup (cell 2)

Run cell 2 (`cell-02-setup`) to load all descriptor files, the GraphQL schema,
and the Workshop 1 file paths.

Expected output:

```
Setup complete.
MCP server descriptors: 5
Phase 1 agent descriptors: 5
GraphQL schema loaded.
Workshop 1 directory: .../agentic-semantic-layer
```

### Step 4 — Run Category 1: Registry completeness (cell 3)

Run cell 3 (`cell-03-cat1-registry`).

Expected output:

```
Category 1: Registry completeness
==================================================
[PASS] 1.1  5 MCP servers are registered
[PASS] 1.2  5 Phase 1 agents are registered
[PASS] 1.3  Consumer Banker discovers at least 4 agents
[PASS] 1.4  Wealth Advisor discovers a different set than Consumer Banker
[PASS] 1.5  referral-rationale-drafter NOT discoverable by Wealth Advisor
[PASS] 1.6  referral-orchestrator discoverable ONLY by Consumer Banker
```

### Step 5 — Run Category 2: Agent posture compliance (cell 4)

Run cell 4 (`cell-04-cat2-posture`).

Expected output:

```
Category 2: Agent posture compliance
==================================================
[PASS] 2.1  nl-to-sparql-agent posture is deterministic-audited
[PASS] 2.2  nl-to-sparql-agent uses embedding model, not text generation
[PASS] 2.3  wealth-signal-detector validates output via SHACL before write
[PASS] 2.4  referral-rationale-drafter output carries is_probabilistic: true
[PASS] 2.5  referral-rationale-drafter output carries requires_human_review: true
[PASS] 2.6  referral-orchestrator rejects invocations without approved_rationale
[PASS] 2.7  referral-orchestrator rejects non-atlas-consumer-banker persona claims
```

### Step 6 — Run Category 3: Four-layer permission model (cell 5)

Run cell 5 (`cell-05-cat3-permissions`).

Expected output:

```
Category 3: Four-layer permission model
==================================================
[PASS] 3.1  persona_claim is present on every MCP server invocation
[PASS] 3.2  Consumer Banker and Wealth Advisor see different capability palettes
[DEFER] 3.3  Consumer Banker query returns fewer customers than BSA Analyst (requires live Neptune)
[DEFER] 3.4  Consumer Banker cannot traverse BSA-restricted named graphs (requires live Neptune)
```

### Step 7 — Run Category 4: Regulatory compliance (cell 6)

Run cell 6 (`cell-06-cat4-regulatory`).

Expected output:

```
Category 4: Regulatory compliance
==================================================
[PASS] 4.1  Compliance banner for non-BSA personas does NOT contain "SAR"
[PASS] 4.2  Compliance banner for non-BSA personas does NOT contain "filed"
[PASS] 4.3  BSA Analyst CAN see SAR-specific detail in the banner
[PASS] 4.4  No probabilistic output committed without human approval
```

### Step 8 — Run Category 5: End-to-end scenario (cell 7)

Run cell 7 (`cell-07-cat5-e2e`). All five assertions in this category require a
running Neptune cluster with synthetic data loaded. If the cluster is not reachable,
all five are marked DEFER rather than FAIL.

Expected output (cluster not running):

```
Category 5: End-to-end Rachel Kim scenario
==================================================
[DEFER] 5.1  Patel household exists in SLGD (requires live Neptune)
[DEFER] 5.2  wealth-signal-detector detects signal for Patel household (requires live Neptune)
[DEFER] 5.3  household-traverser returns >= 2 nodes for Patel household (requires live Neptune)
[DEFER] 5.4  referral-rationale-drafter produces non-empty draft (requires live Neptune)
[DEFER] 5.5  referral-orchestrator routes successfully (requires live Neptune)
[DEFER] 5.6  AuditRecord exists after routing (requires live Neptune)
[DEFER] 5.7  AuditRecord carries PROV-O attribution (requires live Neptune)
```

### Step 9 — Run Category 6: GraphQL schema conformance (cell 8)

Run cell 8 (`cell-08-cat6-graphql`).

Expected output:

```
Category 6: GraphQL schema conformance
==================================================
[PASS] 6.1  Every entity type maps to an ontology class
[PASS] 6.2  Customer query returns uri, customerId
[PASS] 6.3  WealthSignal query returns signalType, strength
[PASS] 6.4  Capability query returns persona-filtered results
```

### Step 10 — Run Category 7: Workshop 1 substrate integrity (cell 9)

Run cell 9 (`cell-09-cat7-integrity`).

Expected output:

```
Category 7: Workshop 1 substrate integrity
==================================================
[PASS] 7.1  No Workshop 1 files modified
[PASS] 7.2  Workshop 1's 22 ontology classes still exist
[PASS] 7.3  Workshop 1's 6 SHACL shapes still exist
[PASS] 7.4  Workshop 2 extensions use atlas-part-2: namespace exclusively
```

### Step 11 — Review the summary (cell 10)

Run cell 10 (`cell-10-summary`) to see the consolidated pass/fail/defer summary.

Expected output (with live Neptune):

```
============================================================
PHASE 1 ACCEPTANCE SUMMARY
============================================================
  Passed:   36
  Failed:    0
  Deferred:  0 (require live infrastructure)
  Total:    36

✓ ALL NON-DEFERRED ASSERTIONS PASS.
  Phase 1 is complete. You may proceed to Phase 2.
```

Expected output (without live Neptune):

```
  Passed:   27
  Failed:    0
  Deferred:  9 (require live infrastructure)
  Total:    36

✓ ALL NON-DEFERRED ASSERTIONS PASS.
  Phase 1 is complete. Deferred assertions will run at deployment.
```

![Phase 1 acceptance summary](/static/images/07-step-11-acceptance-summary.png)

## Expected Outputs

- Categories 1, 2, 4, 6, 7 all pass with zero failures
- Category 3 passes assertions 3.1 and 3.2; 3.3 and 3.4 defer to deployment
- Category 5 defers if Neptune is not running; passes end-to-end if Neptune is running
- Summary prints "ALL NON-DEFERRED ASSERTIONS PASS"

## Troubleshooting

**Category 1 assertion 1.5 fails: referral-rationale-drafter found in Wealth Advisor palette**

Return to [Module 4 — Agent Registry](../04-agent-registry/) and verify the
descriptor file at `spec/04-aws-agent-registry/phase-1-agents/referral-rationale-drafter.json`.
The `discoverable_by` list must contain only `"atlas-consumer-banker"`. Fix the
descriptor file, re-run Module 4 cells 4–6, then re-run this notebook from cell 2.

**Category 2 assertion 2.6 fails: referral-orchestrator accepted without approved_rationale**

The descriptor's `input_schema.required` must list `"approved_rationale"`. If the
check passes locally but the orchestrator function does not enforce the requirement
at call time, the structural check passes but the runtime enforcement does not. Both
must be true. See Module 6 cell 11 for the runtime verification pattern.

**Category 4 assertion 4.1 or 4.2 fails: "SAR" or "filed" found in non-BSA banner**

The `render_compliance_banner()` function returned the wrong message for a non-BSA
persona. Return to [Module 6 — Wholesale UI](../06-wholesale-ui/) and fix cell 5.
The only persona that may see "SAR" is `"atlas-bsa-analyst"`.

**Category 7 assertion 7.1 fails: Workshop 1 files appear modified**

The check compares the current modification time of Workshop 1 key files against
their git-tracked state. If Workshop 1 was legitimately updated before this
workshop run (for example, the TLS fix applied during development), the check
may report a false positive. Verify with `git diff agentic-semantic-layer/` — if
the diff is empty, the files are unchanged and the check has a timing artifact.

## What's Next

Phase 1 is complete. The optional Phase 2 modules extend the system with three
new components:
- [Module 8 — Phase 2 Agents](../08-phase-2-agents/): three Wealth Advisor agents
  powered by AgentCore Memory
- [Module 9 — AgentCore Memory](../09-agentcore-memory/): persistent context for
  advisor conversations
- [Module 10 — Wealth UI](../10-wealth-ui/): the Wealth Advisor UI with JWT auth
  and client-scoped routing
