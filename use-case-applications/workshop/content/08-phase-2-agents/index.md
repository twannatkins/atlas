---
title: "Module 8 — Phase 2 Agents"
weight: 80
---

# Module 8 — Phase 2 Agents

## Learning Objectives

- Explain the three structural differences between Phase 1 and Phase 2 agents:
  data tier (LGD vs SLGD), posture (probabilistic-guarded vs deterministic-audited),
  and state (session memory vs stateless)
- Identify the three Phase 2 agents — `behavioral-signal-agent`,
  `conversational-context-manager`, `theme-summarizer` — and what each adds
- Explain why behavioral signals (EngagementDecay, NetworkInfluence) require the
  LGD's session-level temporal data, which the SLGD's SHACL shapes do not admit
- Verify that the `behavioral-signal-agent` declares LGD access in its descriptor

## Time Estimate

20–25 minutes.

## Prerequisites

- All of Phase 1 (Modules 1–7) complete
- The five Phase 1 agents registered and the Phase 1 acceptance suite passing

## What You Will Build

A comparison of Phase 1 and Phase 2 agent postures and data-tier dependencies, plus
a local run of the `behavioral-signal-agent`'s EngagementDecay detection against
LGD-style session data. This module registers and inspects the three new Phase 2
agents; it does not yet wire them into a UI.

The detection thresholds embedded in each agent's SPARQL FILTER — the dollar amounts
that define what counts as a "large inbound wire" or a "segment shift" — are parameters
your institution's risk and model-risk-management team sets and owns. Workshop 2 uses
illustrative values; in production, those values live in version-controlled SPARQL
alongside the rest of the detection logic, are reviewed under SR 11-7, and can be
changed without touching any application code. The detection structure (the CONSTRUCT
query, the SHACL validation step, the PROV-O attribution) is the reusable architecture
ATLAS provides. The numbers are yours. Workshop 1's Module 5 covers this in depth for
the WS1 signal taxonomy; the same principle applies to every signal type in both
workshops.

The notebook is `notebooks/phase-2-advisor/01_phase_2_agents.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1 (`cell-01-terms`).
The Key Terms table defines "behavioral signal," "EngagementDecay," "NetworkInfluence,"
and "agent posture" as Phase 2 uses them.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/01_phase_2_agents.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains why Phase 2 agents are structurally
different — not incremental additions: they query the LGD for temporal data, carry
probabilistic-guarded postures for statistical-threshold detection, and one of them
(`conversational-context-manager`) maintains state across invocations.

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load all agent descriptors and split them by phase.

Expected output:

```
Total agents loaded:  N
Phase 1 agents:       N
Phase 2 agents:       N

Phase 2 agent names:
  - behavioral-signal-agent (posture: probabilistic-guarded)
  - conversational-context-manager (posture: ...)
  - theme-summarizer (posture: ...)

Setup complete.
```

### Step 4 — Compare postures (cell 4)

Run cell 4 (`cell-04-compare-postures`) to print the posture of every registered
agent, grouped by phase. The `probabilistic-guarded` posture should appear only
in the Phase 2 column.

Expected output:

```
Phase 1 agent postures:
--------------------------------------------------
  nl-to-sparql-agent                  deterministic-audited
  ...
Phase 2 agent postures:
--------------------------------------------------
  behavioral-signal-agent             probabilistic-guarded
  ...
Postures unique to Phase 2: {'probabilistic-guarded'}
```

![Phase comparison output](/static/images/08-step-04-posture-compare.png)

### Step 5 — Run EngagementDecay detection (cell 5)

Run cell 5 (`cell-05-behavioral-agent`) to simulate EngagementDecay detection
against LGD-style session data. Read the cell comment — it explains why a rolling
90-day window is the evidence structure and why the SLGD cannot provide it.

Expected output:

```
Engagement decay detection result:
{ ... }
Signal fired: True
Data source:  lgd (not SLGD)
```

### Step 6 — Inspect MCP server dependencies (cell 6)

Run cell 6 (`cell-06-mcp-deps`) to print each agent's `mcp_servers` and
`graph_tiers` dependencies. Confirm that `behavioral-signal-agent` lists
`graph_tiers: ['lgd']`.

Expected output:

```
MCP server dependencies by phase:
=======================================================
Phase 1 agents:
  nl-to-sparql-agent                  → [atlas-sparql-mcp]
  ...
Phase 2 agents:
  behavioral-signal-agent             → [atlas-sparql-mcp]
                                         graph_tiers: ['lgd']
```

### Step 7 — Verify Phase 2 agent registration (cell 8)

Run cell 8 (`cell-08-verify-exist`) to assert all three Phase 2 agents are
registered.

Expected output:

```
Verifying Phase 2 agent registration...

Expected Phase 2 agents: ['behavioral-signal-agent', 'conversational-context-manager', 'theme-summarizer']
Actual Phase 2 agents:   [...]

[PASS] All 3 expected Phase 2 agents are registered.
```

### Step 8 — Verify LGD access (cell 9)

Run cell 9 (`cell-09-verify-lgd`) to assert that `behavioral-signal-agent`
declares LGD access in its descriptor.

Expected output:

```
Verifying behavioral-signal-agent data tier access...

Agent:        behavioral-signal-agent
Graph tiers:  ['lgd']
MCP servers:  [...]

[PASS] behavioral-signal-agent declares LGD access.
Behavioral signals (EngagementDecay, NetworkInfluence) can be detected.
```

## Expected Outputs

- Phase 2 agent names and postures printed; `probabilistic-guarded` appears in Phase 2 only
- EngagementDecay detection fires with `Data source: lgd (not SLGD)`
- All three Phase 2 agents registered
- `behavioral-signal-agent` declares `graph_tiers: ['lgd']`

## Troubleshooting

**Cell 3 fails: "WARNING: spec/04-aws-agent-registry/agents/ not found"**

The `SPEC_DIR` path is resolved relative to the notebook location. Verify that
`spec/04-aws-agent-registry/agents/` exists under `use-case-applications/` and that
the descriptor JSON files for `behavioral-signal-agent`, `conversational-context-manager`,
and `theme-summarizer` are present.

**Cell 8 fails: Phase 2 agents not found**

The agent descriptor files must include `"phase": 2` at the top level. Open each
Phase 2 descriptor in `spec/04-aws-agent-registry/agents/` and confirm the `phase`
field is set to `2` (integer, not string).

**Cell 9 fails: behavioral-signal-agent does not declare LGD access**

The descriptor's `dependencies.graph_tiers` list must include `"lgd"`. Open
`spec/04-aws-agent-registry/agents/behavioral-signal-agent.json` and add
`"lgd"` to the `graph_tiers` array.

**Cell 4 shows no posture difference between Phase 1 and Phase 2**

If all agents show the same posture, the Phase 2 descriptors are missing or have
the wrong `posture` value. The `behavioral-signal-agent` must be `probabilistic-guarded`;
if it is `deterministic-audited`, the phase comparison will not show the structural
difference the concept section describes.

## What's Next

The behavioral-signal-agent needs to remember what it returned last turn so the
Wealth Advisor can ask follow-up questions. [Module 9 — AgentCore Memory](../09-agentcore-memory/)
builds the session-scoped memory store that enables those multi-turn conversations —
and explains why memory must be session-scoped, not permanent, to comply with GDPR
and CCPA without additional data governance overhead.
