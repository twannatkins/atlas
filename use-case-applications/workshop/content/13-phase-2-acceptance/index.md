---
title: "Module 13 — Phase 2 Acceptance"
weight: 130
---

# Module 13 — Phase 2 Acceptance

## Learning Objectives

- Run the Phase 2 acceptance suite and interpret each of the five categories
- Explain what "architectural validation" means in this context: proving Thesis 2
  (two structurally different UIs consuming the same backbone) rather than testing
  individual features
- Understand why Phase 2 has no deferred assertions — all 20 checks run against
  local descriptors and simulated flows, with no live infrastructure required
- Confirm that all Phase 2 components — agents, memory, JWT auth, cross-UI trail —
  satisfy their acceptance criteria before declaring Phase 2 complete

## Time Estimate

15–20 minutes. Allow extra time if any assertion fails and requires debugging.

## Prerequisites

- All of Modules 8–12 complete
- All module-level verification cells passing

## What You Will Build

Nothing new. This notebook runs the formal Phase 2 acceptance suite from
`notebooks/phase-2-advisor/06_phase_2_acceptance.ipynb`. The suite covers
20 assertions across five categories, all running locally — no live infrastructure
required. Unlike the Phase 1 acceptance suite (Module 7), there are no deferred
assertions.

The acceptance criteria for Phase 2 are defined in the notebook itself. Read cell 1
(`cell-01-concept`) before running any code — it frames the five categories and
explains why this is an architectural validation, not a feature test:

1. **Phase 2 agent registration** — are all three Phase 2 agents registered with
   correct postures and LGD dependencies?
2. **Wealth UI differentiation** — does the Wealth Advisor see different
   capabilities than the Consumer Banker, including `theme-summarizer`?
3. **AgentCore Memory** — is memory session-scoped (cleared at `end_session()`)
   with no cross-session leakage?
4. **JWT authentication** — does the registry filter correctly by JWT persona
   claim, and does a token without a persona claim return empty capabilities?
5. **Cross-UI audit trail** — does the end-to-end flow produce a traceable,
   unbroken audit chain spanning both personas?

The notebook is `notebooks/phase-2-advisor/06_phase_2_acceptance.ipynb`.

## Steps

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/06_phase_2_acceptance.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 1)

Read cell 1 (`cell-01-concept`) for the five categories and the rationale for why
all checks run locally.

### Step 3 — Run setup (cell 2)

Run cell 2 (`cell-02-setup`) to load all agent descriptors and initialize the
results tracker.

Expected output:

```
Agents loaded: N (Phase 2: N)
Running Phase 2 acceptance suite...
```

### Step 4 — Run Category 1: Phase 2 agent registration (cell 3)

Run cell 3 (`cell-03-cat1-registration`).

Expected output:

```
Category 1: Phase 2 agent registration
==================================================

✓ [1.1] 3 Phase 2 agents registered (found N)
✓ [1.2] behavioral-signal-agent is registered
✓ [1.3] conversational-context-manager is registered
✓ [1.4] theme-summarizer is registered
✓ [1.5] behavioral-signal-agent declares LGD graph tier access
```

### Step 5 — Run Category 2: Wealth UI differentiation (cell 4)

Run cell 4 (`cell-04-cat2-wealth-ui`).

Expected output:

```
Category 2: Wealth UI capability differentiation
==================================================

✓ [2.1] Wealth Advisor capabilities differ from Consumer Banker
✓ [2.2] theme-summarizer discoverable by Wealth Advisor
✓ [2.3] conversational-context-manager discoverable by Wealth Advisor
✓ [2.4] referral-orchestrator NOT discoverable by Wealth Advisor
```

### Step 6 — Run Category 3: AgentCore Memory (cell 5)

Run cell 5 (`cell-05-cat3-memory`).

Expected output:

```
Category 3: AgentCore Memory session scope
==================================================

✓ [3.1] Memory stores values during active session
✓ [3.2] Memory clears after end_session()
✓ [3.3] Sessions are isolated (no cross-session leakage)
✓ [3.4] Ending one session does not affect another
```

### Step 7 — Run Category 4: JWT authentication (cell 6)

Run cell 6 (`cell-06-cat4-jwt`).

Expected output:

```
Category 4: JWT authentication
==================================================

✓ [4.1] JWT tokens contain custom:persona claim
✓ [4.2] Registry returns different capabilities for different JWT claims
✓ [4.3] Token without persona claim returns empty capabilities
```

### Step 8 — Run Category 5: Cross-UI audit trail (cell 7)

Run cell 7 (`cell-07-cat5-audit`).

Expected output:

```
Category 5: Cross-UI audit trail
==================================================

✓ [5.1] Audit trail spans both personas
✓ [5.2] Audit trail spans both UIs
✓ [5.3] Parent chain is unbroken (no dangling references)
✓ [5.4] Routing event bridges Wholesale UI to Wealth UI
```

### Step 9 — Review the summary (cell 8)

Run cell 8 (`cell-08-summary`) to see the consolidated result.

Expected output (all passing):

```
============================================================
PHASE 2 ACCEPTANCE SUMMARY
============================================================
  Passed: 20
  Failed: 0
  Total:  20

✓ ALL ASSERTIONS PASS.
  Thesis 2 is validated: two structurally different UIs
  consume the same backbone with correct persona-scoped behavior.

  Phase 2 is complete. The ATLAS architecture supports:
    - Registry-first agent discovery (Thesis 1, Phase 1)
    - Multi-UI backbone consumption (Thesis 2, Phase 2)
    - Behavioral signals via LGD
    - Session-scoped conversational memory
    - JWT-based per-request authorization
    - Cross-UI audit trail with PROV-O attribution
```

![Phase 2 acceptance summary](/static/images/13-step-09-acceptance-summary.png)

## Expected Outputs

- All five categories pass
- 20 assertions pass, 0 fail
- Summary prints `✓ ALL ASSERTIONS PASS` and `Thesis 2 is validated`

## Troubleshooting

**Category 1 assertion 1.5 fails: behavioral-signal-agent does not declare LGD access**

Open `spec/04-aws-agent-registry/agents/behavioral-signal-agent.json` and add
`"lgd"` to the `dependencies.graph_tiers` array. Re-run cell 2 to reload
descriptors, then re-run cell 3.

**Category 2 assertion 2.1 fails: palettes are identical**

The Wealth Advisor and Consumer Banker are seeing the same agents because the
Phase 2 agent descriptors have both personas in their `discoverable_by` lists.
Open the `theme-summarizer`, `conversational-context-manager`, and
`behavioral-signal-agent` descriptors and verify each lists only
`"atlas-wealth-advisor"`. Return to [Module 10 — Wealth UI](../10-wealth-ui/) to
debug.

**Category 3 assertion 3.2 fails: memory not cleared after end_session()**

The `SessionMemory.end_session()` method must remove the session entry entirely
using `self._sessions.pop(sid, None)`. Return to
[Module 9 — AgentCore Memory](../09-agentcore-memory/) and verify cell 4's
implementation.

**Category 4 assertion 4.3 fails: no-persona token returns non-empty capabilities**

`registry_from_jwt()` must return an empty list (or equivalent) when
`payload.get("custom:persona")` is `None`. Add a guard:
`if not persona: return []`. Return to [Module 11 — JWT Authorization](../11-jwt-auth/)
and fix cell 5.

## What's Next

Phase 2 is complete. The ATLAS architecture is validated across both theses.

To deploy to production, run the CDK stack in `use-case-applications/cdk/` —
it provisions Ontop on ECS, AppSync, Cognito user pools, Lake Formation policies,
CloudFront distributions, and the AgentCore Runtime MCP servers. Once deployed,
the Category 5 assertions from Module 7's Phase 1 acceptance suite (end-to-end
Neptune checks deferred to deployment) can be re-run against the live environment.

When you are finished, follow the [Cleanup](../cleanup/) guide to destroy all
provisioned resources and avoid ongoing charges.
