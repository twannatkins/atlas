# 04 — AWS Agent Registry

This section defines every agent and every MCP server that Workshop 2 registers with AWS Agent Registry. Each agent and each MCP server is documented in two paired files:

- **A markdown explainer** (`agents/<name>.md` or `mcp-servers/<name>.md`) — what the agent or server is *for*, what its posture is, what it must not do. This is the teaching layer.
- **A JSON descriptor** (`agents/<name>.json` or `mcp-servers/<name>.json`) — the registration payload submitted to the Agent Registry. This is the executable layer.

Both files are required for each agent and each MCP server. The markdown is read by humans (and Claude Code) to understand purpose; the JSON is read by the registration script to perform the registration.

## The eight agents

Phase 1 registers five agents. Phase 2 adds three more.

| Phase | Agent | Posture |
|---|---|---|
| 1 | `nl-to-sparql-agent` | Deterministic-output, audited |
| 1 | `wealth-signal-detector` | Deterministic, SHACL-driven |
| 1 | `referral-rationale-drafter` | Probabilistic, human-in-the-loop |
| 1 | `household-traverser` | Read-only, SPARQL |
| 1 | `referral-orchestrator` | Workflow, Step Functions |
| 2 | `behavioral-signal-agent` | Deterministic, runs over LGD-derived sessions |
| 2 | `theme-summarizer` | Probabilistic, draft-only |
| 2 | `conversational-context-manager` | Memory-backed, session-scoped |

## The five MCP servers

All five are registered in Phase 1. Phase 2 uses the same five with no additions.

| MCP server | Exposes |
|---|---|
| `atlas-sparql-mcp` | SPARQL query/update over Neptune SLGD |
| `atlas-shacl-mcp` | SHACL shape validation, conformance reports |
| `atlas-er-mcp` | AWS Entity Resolution lookups; MatchID → URI |
| `atlas-fibo-mcp` | FIBO class introspection, ontology browsing |
| `atlas-registry-mcp` | The Agent Registry's own MCP endpoint, used by UIs and Kiro for discovery |

## Postures explained

Each agent has a *posture* that determines how it is used, what audit trail it produces, and what its outputs are allowed to do downstream.

**Deterministic.** Given the same input, produces the same output. Auditable by replay. Used for queries, validations, and traversals where the result must be reproducible. The majority of Workshop 2's agents are deterministic.

**Probabilistic.** Output may vary across invocations. Used only for narrative generation (rationale drafting, theme summarization). Always paired with a human-in-the-loop step before the output affects state.

**Human-in-the-loop.** Output is drafted by the agent and reviewed by a human before being committed. The agent never auto-files, auto-sends, or auto-decides. The human is the final approver.

**Workflow.** Coordinates a sequence of steps via Step Functions. State-changing. Fully audited. Used for orchestration, not for reasoning.

**Memory-backed.** Persists context across invocations via AgentCore Memory. Used only for conversational surfaces where multi-turn context is necessary. Memory is session-scoped and clears at session end.

## How to read this section

If you are learning the architecture, read each agent's markdown explainer in this order:

1. `nl-to-sparql-agent.md` — the foundational agent; the others build on its pattern
2. `wealth-signal-detector.md` — the deterministic signal pattern
3. `household-traverser.md` — the read-only SPARQL pattern
4. `referral-rationale-drafter.md` — the first probabilistic agent; the human-in-the-loop pattern
5. `referral-orchestrator.md` — the workflow pattern
6. Phase 2 agents in any order, after Phase 1 is solid

If you are generating code with Kiro or Claude Code, read the markdown for context, then generate against the JSON descriptors. Each JSON descriptor includes the Lambda code skeleton, the IAM policy template, and the registration payload.

## What must never appear in an agent

Three rules apply to every agent in Workshop 2:

**No agent reasons over raw data.** Agents query SPARQL, invoke SHACL, look up ER. They do not read transaction tables and draw conclusions. The SPARQL query is the reasoning; the agent is the interface.

**No probabilistic agent affects state.** Bedrock-drafted output is always reviewed before it is committed. `referral-rationale-drafter` produces a draft; a human approves the draft; only the approved version is written to the graph.

**No agent bypasses the four-layer permission model.** Every agent invocation carries the user's persona claim. Lake Formation, SHACL named graphs, and registry filters all enforce against that claim. An agent that bypasses any layer is a security issue and a model risk issue simultaneously.

These rules are not negotiable. They are the architectural commitments that make ATLAS compliant.

## The agents directory

Each agent has its own markdown explainer and JSON descriptor under `agents/`. Detail in those files.

## The MCP servers directory

Each MCP server has its own markdown explainer and JSON descriptor under `mcp-servers/`. Detail in those files.

## Test file naming convention

Future agents and MCP servers must follow these conventions for their test files:

1. **Test files are named `test_<component_name>.py`** (not `test_handler.py`). Every component directory contains a `handler.py`, and pytest's default import mode caches module names globally. Identically-named test files across directories cause import collisions when collecting tests. Unique names (`test_atlas_sparql_mcp.py`, `test_nl_to_sparql_agent.py`, etc.) avoid this.

2. **Each component directory contains a `conftest.py`** that adds the directory to `sys.path`. This ensures `from handler import handler` resolves to the local `handler.py` regardless of collection order.

3. **`pytest.ini` at the workspace root uses `--import-mode=importlib`**. This enables pytest's module isolation mode, which treats each test file as an independent import namespace rather than sharing a flat `sys.modules` cache.

All three are required together. Missing any one causes test collection failures when running `pytest use-case-applications/` across all 13 components simultaneously.
