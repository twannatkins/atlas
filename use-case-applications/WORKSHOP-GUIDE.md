# ATLAS workshop guide — the through-line

*The navigational spine for the whole workshop. Read this to see how Workshop 1, Workshop 2,
and the two UIs fit into one story — what is **live today**, what is **possible next**, and
where each claim is taught in depth. Every assertion here links to the notebook that proves
it; nothing here is stated that the running system does not actually do.*

This guide is a map, not a tutorial. The tutorials are the notebooks; the demo script is
[`DEMO.md`](./DEMO.md); the presenter's capstone is
[`07_demo_runbook.ipynb`](./notebooks/phase-2-advisor/07_demo_runbook.ipynb). This page tells
you how they connect.

---

## The one-sentence thesis

> **The LLM is the interface; the graph is the reasoner; governance is structural.** ATLAS
> takes a question a banker would actually ask, answers it from a FIBO-aligned knowledge
> graph through deterministic, SHACL-validated paths, and records every governed action as
> an auditable trail — defensible under SR 11-7.

Everything below is how that sentence is built, layer by layer.

---

## The through-line: Workshop 1 → Workshop 2 → the UIs

The workshops are **sequential**, and each layer is the contract for the next.

### 1. Workshop 1 — the governed substrate (`../agentic-semantic-layer/`)

Workshop 1 builds the thing everything else stands on:

- **A FIBO-aligned ontology.** `atlas:Customer`, `atlas:Account`, `atlas:Holding` are
  grounded in real FIBO classes (`fibo-fnd-pty-pty:IndependentParty`,
  `fibo-fbc-pas-fpas:FinancialAccount`, `fibo-fbc-fi-ip:InvestmentPosition`). This is the
  vocabulary the entire stack speaks. Taught in
  [`02_fibo_alignment.ipynb`](../agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb).
- **SHACL shapes — the deterministic boundary.** A shape, not a model, decides whether a
  triple is allowed into the graph. This is what makes the system defensible: validation is
  a rule your risk team can read, version, and audit. Taught in
  [`06_shacl_boundary.ipynb`](../agentic-semantic-layer/notebooks/06_shacl_boundary.ipynb).
- **R2RML mappings and a two-tier Neptune deployment** (LGD → SLGD), with PROV-O provenance
  on every derived fact.

**Workshop 2 never modifies Workshop 1.** It reads the ontology as a contract and extends it
only under the `atlas-part-2:` namespace.

### 2. Workshop 2 — agents, API, and the governed actions (this directory)

Workshop 2 builds the behaviour on top of the substrate:

- **The Agent Registry** answers *"what capabilities exist for this persona?"* — live, never
  hardcoded. Taught in [`03_agent_registry.ipynb`](./notebooks/phase-1-referral/03_agent_registry.ipynb).
- **Agents that refuse to invent.** `nl-to-sparql-agent` matches a question to a *validated
  SPARQL template* (cosine ≥ 0.75) and runs that — it never free-generates SPARQL.
  `referral-rationale-drafter` (Bedrock) drafts only from grounded context and is badged
  *requires human review*. Why they behave this way is in
  [`04a_how_agents_work.ipynb`](./notebooks/phase-1-referral/04a_how_agents_work.ipynb).
- **Wealth signals are DERIVED outputs, not inputs.** *Large Deposit Pattern* (deposit
  ≥ $250,000, no active coverage) and *No Advisor Coverage* are computed from the graph and
  validated before they are written — nobody types them in. Taught in
  [`05_wealth_signals.ipynb`](./notebooks/phase-1-referral/05_wealth_signals.ipynb) and built
  in [`05a_wealth_signals_build.ipynb`](./notebooks/phase-1-referral/05a_wealth_signals_build.ipynb).
- **A FIBO-shaped GraphQL API** every type of which maps to an ontology class. Taught in
  [`04_graphql_federation.ipynb`](./notebooks/phase-1-referral/04_graphql_federation.ipynb).

### 3. The UIs — two lenses on one backbone

Two Next.js applications consume the *same* schema and registry:

- **Wholesale UI** — the Consumer Banker's referral workbench (Dana Brooks).
- **Wealth UI** — the Wealth Advisor's coverage workbench (Marcus Webb).

They differ only in which fragments they query and which persona they claim. That is
**Thesis 2: two UIs, one backbone.** The end-to-end story they tell — banker finds a
candidate, drafts a rationale, routes it through a governed workflow, advisor receives and
accepts the handoff — is scripted in [`DEMO.md`](./DEMO.md).

---

## The real topology — what actually runs when you click

This is the most important thing to get right, because earlier drafts of ATLAS described a
topology the running system does not use. **Here is the truth, and it is what
[`04_graphql_federation.ipynb`](./notebooks/phase-1-referral/04_graphql_federation.ipynb)
now teaches:**

| Path | Used for | How it runs | Latency |
|---|---|---|---|
| **Read — direct Neptune** | dashboard, Client 360, signals, coverage, audit trail | resolver Lambda queries Neptune **directly** (SigV4, in-VPC). **No agent, no MCP in the loop.** | ~1 s warm |
| **Action — resolver → agent** | *Ask the graph*, *Generate draft*, *Converse* | resolver invokes an **AgentCore Runtime** (`invoke_agent_runtime`) | ~10 s cold, then fast |
| **Action — routing** | *Approve and route* | resolver starts the `referral-orchestrator` **Step Functions** workflow | a few seconds |
| **Gate — SHACL** | every `RoutingDecision`, every signal write | a **SHACL shape** decides pass/fail — deterministic | instant |

The read path is direct-to-Neptune for **speed**: putting the ~5 s AgentCore invoke floor
behind every UI field was too slow, so reads bypass the agent entirely. The MCP path remains
as a fallback and for governed writes.

---

## Live today vs. possible next

A guide that only described what works would be marketing. Here is the honest split. The
**live** column is demonstrable right now; the **possible next** column is real roadmap,
labelled as such — never present it as working.

| Capability | Live today | Possible next (roadmap) |
|---|---|---|
| **Access control** | The persona claim (Cognito group) gates *which fields a caller may invoke* — AppSync authorization + each agent's `VALID_PERSONAS` allow-list. A disallowed persona is refused the call. | — |
| **Row-level data scoping** | *Not enforced.* The direct-Neptune read path returns the same rows regardless of persona. | Per-advisor / per-persona **Lake Formation** row scoping over Ontop-translated Iceberg, so the *same* field returns a *different row set* per persona. |
| **Ask the graph** | Template-bounded NL→SPARQL (a fixed, validated set); honest *no-match* when nothing fits. | A larger template library; richer question coverage. |
| **Conversation** | Single-turn: `converse` answers each question independently; `priorTurns` is always 0. | **Multi-turn memory** — AgentCore Memory wired so a follow-up question carries prior context (the `get_memory`/`put_memory` ops are not real yet). |
| **Capabilities palette** | A live **registry display** — shows what exists for the persona. | **Click-to-invoke** from the palette (the dashed *"Invoke from palette · next"* row is honest about this). |
| **Wealth signals** | *Large Deposit Pattern*, *Household Aggregation*, and a *No Advisor Coverage* marker are derived from real synthetic data. | The other three taxonomy signals (*Equity Event*, *Retirement Rollover*, *Business Sale Liquidity*) — defined in the ontology but not derived, because there is no source data for them yet. |
| **RM Session Intelligence / behavioral signals** | Defined as agents/classes (`behavioral-signal-agent`, `atlas-part-2:` behavioral signals). | Surfaced live in the Wealth UI as an advisor-prep panel. |

**The platform-economics story.** The reason to split *who can call what* (live) from *which
rows you see* (roadmap) is that the access-control layer is cheap and structural — it rides on
Cognito and the registry — while row scoping is a data-plane investment (Ontop + Lake
Formation + Iceberg) you make once and reuse across every new UI and persona. The architecture
**scales by addition**: a new persona is a new Cognito group and a registry entry, not a new
backend.

---

## How to use this guide

- **Presenting the demo?** Read [`DEMO.md`](./DEMO.md) for the five-act story, then drive it
  from the browser; use [`07_demo_runbook.ipynb`](./notebooks/phase-2-advisor/07_demo_runbook.ipynb)
  to show the live data behind each card.
- **Teaching the architecture?** Follow the notebooks in order; this guide is the index of
  *why each one exists* and *how it connects to the next*.
- **Asked "is this real?"** Use the **Live today vs. possible next** table. If it is in the
  left column, demonstrate it. If it is in the right column, say "roadmap" — and mean it.

---

## The FIBO grounding (where the vocabulary comes from)

Every entity the UIs render is FIBO-grounded in Workshop 1. When someone asks "where does
`Customer` come from?", the answer is not "we made it up" — it is
`fibo-fnd-pty-pty:IndependentParty`, aligned in
[`02_fibo_alignment.ipynb`](../agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb) and
declared in the GraphQL schema's type docstrings. That grounding is what lets a banking
audience trust that the model is speaking their regulatory language, not a bespoke one.
