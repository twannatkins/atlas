---
title: "Module 6 — Wholesale UI: The Two-Driver Architecture"
weight: 60
---

# Module 6 — Wholesale UI: The Two-Driver Architecture

## Learning Objectives

- Explain the two-driver architecture: GraphQL drives what data is rendered, the
  Agent Registry drives what actions are available — and neither is hardcoded
- Implement and verify the compliance banner that respects the tipping-off
  prohibition under 31 U.S.C. §5318(g)(2)
- Confirm that the "Route to advisor" action requires an `approved_rationale`
  before the `referral-orchestrator` agent will accept the invocation
- Trace the complete Rachel Kim scenario from signal detection through routing

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 5 — GraphQL Federation](../05-graphql-federation/) complete
- All three resolver patterns verified

## What You Will Build

A simulated Wholesale UI that demonstrates the two-driver architecture:
`entity_360_data` (from GraphQL), a persona-scoped capability palette (from the
Agent Registry), a compliant compliance banner (tipping-off safe), and the
human-in-the-loop routing gate.

The notebook is `notebooks/phase-1-referral/06_wholesale_ui.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`). The Key Terms table defines "two-driver architecture,"
"capability palette," and "human-in-the-loop" as used in this notebook.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/06_wholesale_ui.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains the two-driver pattern:

Most enterprise applications have one driver: an API that returns data, and the
UI renders it. The set of actions available to the user is hardcoded in the UI
code — a button exists because a developer put it there. The Wholesale UI has two
drivers. The first is the FIBO-shaped GraphQL API — it provides entity data for
the Entity 360 panel. The second is the Agent Registry — it provides a
persona-scoped capability palette that tells the UI what actions the current user
is allowed to invoke. Neither is hardcoded; both are queried live. A new agent
registered in the registry appears in the palette automatically.

The concept section also explains the regulatory constraint that governs the
compliance banner.

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and agent descriptors.

Expected output:

```
Shared helpers loaded.
Agent descriptors loaded: N
```

### Step 4 — Simulate the Entity 360 data fetch (cell 4)

Run cell 4 (`cell-04-entity-360`) to build the `entity_360_data` dict that
the GraphQL API would return for the Patel household. Read the simulated response —
it shows which fields come from Ontop (entity data in Iceberg) and which come from
direct Neptune SPARQL (WealthSignal instances).

Expected output:

```
Entity 360 — Patel household
  uri: atlas:hh/9c2a1e
  label: Patel Household
  members: [Anjali Patel, ...]
  wealth_signals: [LargeDepositPattern, ...]
  compliance_review: True
```

### Step 5 — Implement the compliance banner (cell 5)

Run cell 5 (`cell-05-compliance-banner`) to implement `render_compliance_banner()`.
Read the cell comment carefully — it explains why the banner text must say
"Active compliance review — contact BSA team before client outreach" and must
never say "SAR filed."

The tipping-off prohibition (31 U.S.C. §5318(g)(2)) makes it a federal crime to
disclose to a customer or a non-BSA employee that a SAR has been filed. The
Consumer Banker is outside the BSA function. The banner tells them only what they
are allowed to know.

Expected output:

```
Consumer Banker banner: "Active compliance review — contact BSA team before client outreach"
BSA Analyst banner:     "SAR draft in progress — BSA team review required"
No banner (no review):  None
```

### Step 6 — Implement the capability palette (cell 6)

Run cell 6 (`cell-06-capability-palette`) to implement `get_capability_palette()`.
This calls `discover_capabilities()` from Module 4 and returns the persona-scoped
action list.

Expected output:

```
Consumer Banker palette: N capabilities
  - nl-to-sparql-agent
  - wealth-signal-detector
  - household-traverser
  - referral-rationale-drafter
  - referral-orchestrator
Wealth Advisor palette:  M capabilities (referral-rationale-drafter absent)
```

![Capability palette by persona](/static/images/06-step-06-capability-palette.png)

### Step 7 — Simulate Route to advisor (cell 7)

Run cell 7 (`cell-07-route-to-advisor`) to simulate the complete "Route to
advisor" flow: the Consumer Banker selects the Patel household, the
`referral-rationale-drafter` agent drafts a narrative, the banker reviews and
approves the draft, and the `referral-orchestrator` agent routes the referral.

Expected output:

```
Route to advisor — Patel household
  Step 1: wealth-signal-detector → signals detected: N
  Step 2: referral-rationale-drafter → draft created (is_probabilistic: True)
  Step 3: [Human review gate] approved_rationale: "..."
  Step 4: referral-orchestrator → routed
  AuditRecord written: atlas:audit/...
```

### The demo loop — Dana's half

In the live demo, this is the first half of the route → banner → take-on → reset
loop. As **Dana Brooks (the Consumer Banker)** you: open the signalled customer
**Rachel Kim**, click **Route referral → Generate draft** (grounded, probabilistic,
requires review), then **Approve and route**. The outcome you trigger: Rachel lands
in **Marcus Webb (the Wealth Advisor)**'s book flagged **"New — routed to you."**
Marcus's half — the banner, **Take on client** (a real `takenOnAt` that clears it),
and **Reset** — is in [Module 10 — The Wealth UI](../10-wealth-ui/) and the full
walk in [Module 12 — End-to-End](../12-end-to-end/). Switching personas is just
**Sign out** (top-right). The canonical script is `use-case-applications/DEMO.md`.

### Step 8 — Verify persona-scoped palette (cell 9)

Run cell 9 (`cell-09-verify-palette`) to assert the two palette assertions from
the acceptance criteria: Consumer Banker sees `referral-orchestrator`, and Wealth
Advisor does not see `referral-rationale-drafter`.

Expected output:

```
[PASS] Consumer Banker palette contains referral-orchestrator.
[PASS] Wealth Advisor palette does not contain referral-rationale-drafter.
```

### Step 9 — Verify compliance banner (cell 10)

Run cell 10 (`cell-10-verify-banner`) to assert that the banner for non-BSA
personas never contains the strings "SAR" or "filed."

Expected output:

```
Checking non-BSA personas: atlas-consumer-banker, atlas-wealth-advisor, atlas-ontology-steward
  atlas-consumer-banker: no SAR/filed strings  ✓
  atlas-wealth-advisor:  no SAR/filed strings  ✓
  atlas-ontology-steward: no SAR/filed strings  ✓
[PASS] Tipping-off prohibition respected for all non-BSA personas.
```

### Step 10 — Verify human-in-the-loop (cell 11)

Run cell 11 (`cell-11-verify-human-in-loop`) to assert that the
`referral-orchestrator` descriptor's `input_schema` declares `approved_rationale`
as a required field — the structural guarantee that no auto-routing can occur.

Expected output:

```
[PASS] referral-orchestrator requires approved_rationale (human-in-the-loop enforced).
```

## Expected Outputs

- Entity 360 data includes both GraphQL entity fields and Neptune WealthSignal instances
- Compliance banner never contains "SAR" or "filed" for non-BSA personas
- Capability palette differs by persona; Wealth Advisor lacks `referral-rationale-drafter`
- Route to advisor simulation writes an `AuditRecord` with PROV-O attribution
- All three verify cells print `[PASS]`

## Troubleshooting

**Cell 5 banner contains "SAR" for a non-BSA persona**

The `render_compliance_banner()` implementation returned the wrong branch for the
persona. Check the conditional logic: only `"atlas-bsa-analyst"` should receive the
SAR-containing message. Every other persona — including `"atlas-ontology-steward"` —
is outside the BSA function and must receive the generic compliance message.

**Cell 7 raises KeyError on approved_rationale**

The Route to advisor simulation passes an `approved_rationale` string to
`simulate_route_to_advisor()`. If the parameter name does not match the function
signature, Python raises KeyError when the orchestrator checks the required field.
Verify that the function signature uses `approved_rationale` (not `rationale` or
`approved_narrative`).

**Cell 9 fails: Wealth Advisor sees referral-rationale-drafter**

Return to [Module 4 — Agent Registry](../04-agent-registry/) and verify that the
`referral-rationale-drafter` descriptor lists only `"atlas-consumer-banker"` in
`discoverable_by`. Then re-run cell 3 in this notebook (which reloads the
descriptors) before re-running cell 9.

**Cell 11 fails: approved_rationale not in required fields**

The `referral-orchestrator` descriptor's `input_schema.required` must include
`"approved_rationale"`. Open
`spec/04-aws-agent-registry/phase-1-agents/referral-orchestrator.json` and verify
the schema. This is also an acceptance criteria check (assertion 2.6).

## What's Next

Phase 1 is assembled. [Module 7 — Phase 1 Acceptance](../07-phase-1-acceptance/)
runs the full acceptance suite from `spec/10-acceptance-criteria.md`: 24 assertions
across seven categories. Every assertion that passes is a contract honored — a
piece of the architecture that works as specified. If all non-deferred assertions
pass, Phase 1 is complete and you may proceed to Phase 2.
