---
title: "Module 4 — Agent Registry: Discovery and Governance"
weight: 40
---

# Module 4 — Agent Registry: Discovery and Governance

## Learning Objectives

- Explain what problem the Agent Registry solves — and why a hardcoded capability
  list is the wrong answer for a governed, multi-persona application
- Load MCP server and Phase 1 agent descriptors from the spec directory and
  register them into a local registry
- Implement `discover_capabilities(persona_claim)` and verify that Consumer Banker
  and Wealth Advisor see different capability palettes
- Confirm that `referral-rationale-drafter` is visible only to Consumer Banker —
  and explain why this restriction maps to a regulatory requirement

## Time Estimate

20–25 minutes.

## Prerequisites

- [Module 3 — MCP Servers](../03-mcp-servers/) complete
- `sparql_mcp_query()` implemented and shape-verified

## What You Will Build

A local Agent Registry backed by JSON descriptors from
`spec/04-aws-agent-registry/`. The registry exposes
`discover_capabilities(persona_claim)` and returns a persona-scoped list of
registered agents and MCP server operations. The Consumer Banker and Wealth
Advisor palettes are verified to differ at the end of the notebook.

The notebook is `notebooks/phase-1-referral/03_agent_registry.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`). The Key Terms table defines "descriptor," "capability palette,"
and "posture" as used in the registry and in later acceptance criteria.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/03_agent_registry.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why capability palettes must be registry-driven, not hardcoded
- How a JSON descriptor declares an agent's operation schema, posture, and
  `discoverable_by` list
- Why `referral-rationale-drafter` is restricted to Consumer Banker (the agent
  drafts narratives that are only appropriate in the referral workflow — surfacing
  it to Wealth Advisors would expose an action that has no valid use in their flow)

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and establish the spec
directory path.

Expected output:

```
Shared helpers loaded.
Spec directory: .../spec/04-aws-agent-registry
Subdirectories: mcp-servers/, phase-1-agents/
```

### Step 4 — Load MCP server descriptors (cell 4)

Run cell 4 (`cell-04-load-descriptors`) to read all JSON descriptor files from
`spec/04-aws-agent-registry/mcp-servers/` and `spec/04-aws-agent-registry/phase-1-agents/`.

Expected output:

```
MCP server descriptors loaded: 5
Phase 1 agent descriptors loaded: 5
```

### Step 5 — Register MCP servers (cell 5)

Run cell 5 (`cell-05-register-mcp`) to insert the five MCP server descriptors
into the local registry.

Expected output:

```
Registered: atlas-sparql-mcp
Registered: atlas-shacl-mcp
Registered: atlas-entity-resolution-mcp
Registered: atlas-fibo-mcp
Registered: atlas-registry-mcp
Registry size: 5 MCP servers
```

### Step 6 — Register Phase 1 agents (cell 6)

Run cell 6 (`cell-06-register-agents`) to insert the five Phase 1 agent
descriptors.

Expected output:

```
Registered: nl-to-sparql-agent
Registered: wealth-signal-detector
Registered: household-traverser
Registered: referral-rationale-drafter
Registered: referral-orchestrator
Registry size: 5 agents
```

### Step 7 — Implement discover_capabilities() (cell 7)

Run cell 7 (`cell-07-discovery-function`) to define
`discover_capabilities(persona_claim)`. The function filters the registry by
the `discoverable_by` list on each descriptor and returns the matching entries.

Expected output:

```
discover_capabilities() defined.
Consumer Banker palette: N capabilities
Wealth Advisor palette:  N capabilities
```

![Capability palette discovery output](/static/images/04-step-07-discovery-output.png)

### Step 8 — Verify Consumer Banker palette (cell 9)

Run cell 9 (`cell-09-verify-consumer-banker`) to assert that Consumer Banker
discovers at least 4 agents including `referral-orchestrator`.

Expected output:

```
Consumer Banker capability check
  Capabilities discovered: N (expected >= 4)
  referral-orchestrator: PRESENT
[PASS] Consumer Banker palette is correct.
```

### Step 9 — Verify Wealth Advisor palette (cell 10)

Run cell 10 (`cell-10-verify-wealth-advisor`) to assert that Wealth Advisor does
NOT discover `referral-rationale-drafter`.

Expected output:

```
Wealth Advisor capability check
  referral-rationale-drafter: NOT IN PALETTE (correct)
[PASS] Wealth Advisor cannot discover the Consumer Banker referral agent.
```

## Expected Outputs

- 5 MCP servers and 5 Phase 1 agents registered into the local registry
- Consumer Banker discovers at least 4 agents including `referral-orchestrator`
- Wealth Advisor palette does not include `referral-rationale-drafter`
- Both verify cells print `[PASS]`

## Troubleshooting

**Cell 4 fails: "No JSON files found in spec/04-aws-agent-registry/mcp-servers/"**

The spec directory path is resolved relative to the notebook file. If the notebook
is opened from a directory other than `notebooks/phase-1-referral/`, the relative
path will be wrong. The cell uses `os.path.join(SPEC_DIR, subdir)` where `SPEC_DIR`
is set in cell 3 — print `SPEC_DIR` to verify the resolved absolute path, then
confirm the descriptor files exist at that location.

**Cell 9 fails: "Consumer Banker discovers fewer than 4 agents"**

Check the `discoverable_by` list in each Phase 1 agent descriptor file. Every agent
that should be visible to Consumer Banker must include `"atlas-consumer-banker"` in
that list. Open `spec/04-aws-agent-registry/phase-1-agents/` in the file explorer
and verify the descriptor JSON.

**Cell 10 fails: "referral-rationale-drafter found in Wealth Advisor palette"**

The `referral-rationale-drafter` descriptor's `discoverable_by` list must not
include `"atlas-wealth-advisor"`. Open
`spec/04-aws-agent-registry/phase-1-agents/referral-rationale-drafter.json` and
verify the list contains only `"atlas-consumer-banker"`.

**Cell 7 produces identical palettes for all personas**

`discover_capabilities()` is not filtering on `discoverable_by`. The filter
condition is `persona_claim in descriptor["registry_metadata"]["discoverable_by"]`.
Verify the path matches the actual descriptor key name.

## What's Next

The registry knows what capabilities exist and who can see them. But how does a
UI consume both the entity data and the capability palette at the same time?
[Module 5 — GraphQL Federation](../05-graphql-federation/) introduces the
FIBO-shaped GraphQL schema and its three resolver patterns — the data driver that
works alongside the registry-driven capability driver.
