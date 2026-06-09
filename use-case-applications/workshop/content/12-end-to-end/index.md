---
title: "Module 12 — End-to-End Walkthrough"
weight: 120
---

# Module 12 — End-to-End Walkthrough

## Learning Objectives

- Trace the complete cross-UI advisor flow: signal detection in the Wholesale UI
  through referral routing to conversational follow-up in the Wealth UI
- Explain why the routing decision is the structural bridge between the two UIs —
  the PROV-O AuditRecord that references both the Consumer Banker's signal and the
  Wealth Advisor's notification
- Verify that the full audit trail spans both personas with an unbroken parent chain
- Confirm that the routing event links both UIs bidirectionally

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 11 — JWT Authorization](../11-jwt-auth/) complete
- JWT persona claim verified and registry filtering confirmed

## What You Will Build

A six-step simulation of the complete cross-UI flow, assembled into a full audit
trail. The simulation builds plain Python event dicts — no live infrastructure
required. The audit trail structure is what a compliance officer would query from
the graph after a real deployment.

The notebook is `notebooks/phase-2-advisor/05_end_to_end.ipynb`.

This notebook simulates the cross-UI flow locally. In production, each step
involves live AWS services (Neptune, AppSync, AgentCore, Cognito) and real network
calls; the event structure and audit trail shape are identical.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1 (`cell-01-terms`).
The Key Terms table defines "cross-UI flow," "routing decision," the "New — routed
to you" banner → take-on, and "conversational follow-up."

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/05_end_to_end.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why the flow crosses the UI boundary at the routing decision
- The route → banner → take-on → reset loop: Dana routes → Marcus sees **"New —
  routed to you"** (`routedByWorkflow && !takenOnAt`, a real state) → **Take on
  client** writes a real `atlas:takenOnAt` and clears the banner (parallel to
  unchanged coverage) → **Reset** returns the graph to seed state
- How the routing decision creates a PROV-O AuditRecord that links both UIs
- Why Thesis 2 requires connected workflows — not just different views of data,
  but actions in one UI producing effects in the other

This page is the runner-altitude view; the canonical presenter script is
`use-case-applications/DEMO.md`. The per-persona halves are in
[Module 6 — Wholesale UI](../06-wholesale-ui/) (Dana) and
[Module 10 — The Wealth UI](../10-wealth-ui/) (Marcus).

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load helpers.

Expected output:

```
Setup complete.
This notebook simulates the cross-UI flow locally.
```

### Step 4 — Step 1: Signal detected (cell 4)

Run cell 4 (`cell-04-step1-detect`) to create the signal detection event in the
Wholesale UI. Read the event dict — note the `audit_id` that will anchor the
entire chain.

Expected output:

```
Step 1: Signal detected in Wholesale UI
{
  "step": 1,
  "action": "signal_detected",
  "persona": "atlas-consumer-banker",
  "ui": "Wholesale UI",
  "agent": "wealth-signal-detector",
  "client_uri": "atlas:client-rachel-kim",
  "signal_type": "EngagementDecay",
  ...
}
```

### Step 5 — Steps 2–3: Draft and route (cell 5)

Run cell 5 (`cell-05-step2-draft`) to simulate rationale drafting (with banker
approval) and routing. The routing event carries `parent_audit_id` pointing to
the rationale, which itself points to the signal — the backward chain.

Expected output:

```
Step 2: Rationale drafted and approved
  Rationale: Client shows significant engagement decay (decay ratio 0.111). ...
  Approved by: dana.brooks (Consumer Banker — the gate)

Step 3: Referral routed
  Routed to: marcus.webb (Wealth Advisor)
  routedByWorkflow: True  takenOnAt: None
  → In the Wealth UI this shows as the 'New — routed to you' banner
    (routedByWorkflow && !takenOnAt).
```

### Step 6 — Steps 4–6: Advisor sees the banner, takes the client on (cell 6)

Run cell 6 (`cell-06-step4-receive`) to simulate the Wealth Advisor's side: the
**"New — routed to you"** banner shown, **Take on client** (a real `atlas:takenOnAt`
that clears the banner, parallel to unchanged coverage), and a single-turn
conversational follow-up. Note the `parent_audit_id` chaining banner → take-on.

Expected output:

```
Step 4: 'New — routed to you' banner shown in Wealth UI
  banner_shown (routedByWorkflow && !takenOnAt): True

Step 5: Take on client
  takenOnAt written: ...  → banner_cleared: True
  coverage_unchanged (isActive/coverageStartDate untouched): True

Step 6: Conversational follow-up (single-turn)
  Question:   What is this client's current AUM and engagement trend?
  priorTurns: 0 (AgentCore Memory not wired)
```

### Step 7 — Assemble and inspect the audit trail (cell 7)

Run cell 7 (`cell-07-audit-trail`) to assemble all six events into a single trail
and print the chain. Verify that each event's `parent_audit_id` points to the
prior event's `audit_id`.

Expected output:

```
Full cross-UI audit trail:
============================================================
  Step 1: [Wholesale UI] signal_detected
           persona: atlas-consumer-banker
           audit_id: XXXXXXXX...
  Step 2: [—           ] rationale_drafted
           persona: atlas-consumer-banker
           parent:   XXXXXXXX...
  Step 3: [—           ] referral_routed
           ...
  Step 4: [Wealth UI   ] new_routed_banner_shown
           persona: atlas-wealth-advisor
           parent:   XXXXXXXX...
  Step 5: [Wealth UI   ] take_on_client
  Step 6: [Wealth UI   ] conversational_followup

Personas spanned: ['atlas-consumer-banker', 'atlas-wealth-advisor']
UIs spanned:      ['Wealth UI', 'Wholesale UI']
```

![Full audit trail](/static/images/12-step-07-audit-trail.png)

### Step 8 — Verify the audit trail (cell 9)

Run cell 9 (`cell-09-verify-trail`) to assert the trail spans both personas with
no broken parent links.

Expected output:

```
Verifying audit trail spans both personas...

Personas in audit trail: ['atlas-consumer-banker', 'atlas-wealth-advisor']
Expected personas:       ['atlas-consumer-banker', 'atlas-wealth-advisor']

Broken parent links: none

[PASS] Audit trail spans both personas with unbroken parent chain.
```

### Step 9 — Verify routing links both UIs (cell 10)

Run cell 10 (`cell-10-verify-routing`) to assert the routing event bridges
both directions: forward to the Wealth UI notification, backward to the
Wholesale UI signal.

Expected output:

```
Verifying routing decision links both UIs...

Forward link (routing → banner shown): True
Backward link (routing ← rationale ← signal): True

Routing persona:      atlas-consumer-banker
Banner-shown persona: atlas-wealth-advisor
Spans both personas:  True

Banner shown then cleared by take-on (real transition): True

[PASS] Routing decision correctly links both UIs.
The cross-UI workflow — route → banner → take-on → clear — is fully traceable.
```

## Expected Outputs

- Six-step audit trail assembled and printed with personas and UI labels
- Trail spans `['atlas-consumer-banker', 'atlas-wealth-advisor']` and both UI names
- Broken parent links: none
- Both verify cells print `[PASS]`

## Troubleshooting

**Cell 9 fails: "Audit trail does not span both personas"**

The `audit_trail` list must contain at least one event with `persona:
atlas-consumer-banker` and at least one with `persona: atlas-wealth-advisor`.
If all events carry the same persona, the Wholesale UI steps (cells 4–5) may have
used the wrong persona string. Check that `signal_event["persona"]` is
`"atlas-consumer-banker"` and `notification_event["persona"]` is
`"atlas-wealth-advisor"`.

**Cell 9 fails: "Broken parent links"**

Each event's `parent_audit_id` must appear in the `audit_ids` set from a prior
event. If a parent ID was generated freshly (e.g., `str(uuid.uuid4())`) instead
of copied from the prior event's `audit_id`, the chain breaks. Cells must be
run in order and each event must carry the `audit_id` of the event it follows.

**Cell 10 fails: "Forward link is False"**

The notification event's `parent_audit_id` must equal the routing event's
`audit_id`. Check cell 6 — `notification_event["parent_audit_id"]` must be set
to `routing_event["audit_id"]`, which is defined in cell 5.

**Cell 5 raises NameError: "routing_event not defined"**

Cell 5 defines both `rationale_event` and `routing_event`. If cell 5 raised an
error mid-way through, `routing_event` may not be defined when cell 6 runs.
Re-run cell 5 from the top; if it fails, check that `signal_event` is still
defined (re-run cell 4 first).

## What's Next

The cross-UI flow is complete. [Module 13 — Phase 2 Acceptance](../13-phase-2-acceptance/)
runs the full acceptance suite to confirm that all Phase 2 components — agent
registration, Wealth UI differentiation, AgentCore Memory, JWT auth, and the
cross-UI audit trail — satisfy the 20 assertions that together validate Thesis 2.
