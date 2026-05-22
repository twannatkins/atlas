# 01 — Architecture

The architectural thesis that governs every other section of this spec. Read this before reading any other section. The decisions documented here propagate downstream into the agent registry, the GraphQL schema, the React components, the CDK stack, and the notebook teaching sequence.

This document is also the primary teaching anchor for the *why* of Workshop 2. Each section ends with the notebook where the novice meets the concept in working form.

## The four theses

Workshop 2's architecture rests on four theses. Each is a deliberate choice with alternatives that were considered and rejected.

### Thesis 1 — Registry-first agent discovery

Every agent and every MCP server is registered in AWS Agent Registry — the managed AWS service for agent and tool discovery — before any UI knows it exists. The UI queries the registry to learn what capabilities to render; the registry filters its response by the user's persona claim. This is the *capability palette* you see on every Workshop 2 screen.

**MCP-first by design.** AWS Agent Registry supports three record types — MCP, Agent (A2A), and CUSTOM. Workshop 2 uses MCP for nearly everything because the MCP protocol fits the way our components are actually invoked: a UI or an agent sends a structured request, the component returns a structured response, the round-trip is synchronous. This applies to our five capability servers (`atlas-sparql-mcp`, `atlas-shacl-mcp`, `atlas-er-mcp`, `atlas-fibo-mcp`, `atlas-registry-mcp`) and to all seven of our standalone agents (`nl-to-sparql-agent`, `wealth-signal-detector`, `household-traverser`, `referral-rationale-drafter`, `behavioral-signal-agent`, `theme-summarizer`, `conversational-context-manager`). Twelve MCP records, one uniform discovery and invocation interface.

**The one exception.** `referral-orchestrator` wraps a Step Functions state machine and runs asynchronously — the caller starts a workflow, gets an execution ARN, and polls for completion later. The MCP protocol assumes synchronous request-response semantics; pretending Step Functions fits that model would hide its actual async nature from callers. So `referral-orchestrator` is registered as CUSTOM, with metadata describing its workflow lifecycle. This is the only architectural carve-out for a non-MCP record type in Workshop 2.

**The alternative considered and rejected.** Hardcoding agent endpoints in the UI. This works on day one and rots immediately — every new agent requires a UI deploy, every persona change requires a UI deploy, every capability sunset requires a UI deploy. The registry-first pattern decouples the UI from the agent inventory.

**The deeper reason.** Governance. AWS Agent Registry's DRAFT → PENDING_APPROVAL → APPROVED workflow makes every registered capability a deliberate act with explicit human review. Every approved record is a documented attack surface, a documented MRM submission, a documented auditable component. The registry's approval workflow is the gate — an organization that lets developers wire agents directly into UIs has no equivalent control point.

**Where the novice meets this.** Notebook `03_agent_registry.ipynb` — the first time you query the registry from a UI and see the capability palette populate live, and the first time you push a new agent through the DRAFT → PENDING_APPROVAL → APPROVED workflow.

### Thesis 2 — Two UIs, one backbone

Phase 1 builds a Wholesale UI for Consumer Banker referrals. Phase 2 builds a Wealth UI for the advisor workbench. Both consume the same FIBO-shaped GraphQL API. Both query the same Agent Registry. Both query the same Neptune SLGD. The differences are entirely in the *lens*, not the *substrate*.

**The alternative considered and rejected.** Two separate backends, one per UI. This is the path most enterprises drift into — the wealth team builds its own API because the consumer team's API doesn't have the fields they need. Six months later there are five backends, four ontologies, and zero composability across lines of business.

**The deeper reason.** The two-UI design proves the substrate is reusable. One UI proves nothing. Two UIs proves the FIBO-shaped GraphQL schema can serve structurally different applications. Five UIs would prove the same thing with redundant effort. Two is the minimum demonstration of the thesis.

**Where the novice meets this.** Notebook `05_wholesale_ui.ipynb` in Phase 1, then `03_wealth_ui.ipynb` in Phase 2. The teaching moment is when the novice sees the same `fibo:Party.advisoryRelationship` GraphQL fragment render differently in the two UIs because the resolver respects the persona's data scope.

### Thesis 3 — LLM at the edges, never in the middle

Bedrock foundation models appear in three places in Workshop 2: translating natural language to SPARQL (`nl-to-sparql-agent`), drafting referral rationale narratives (`referral-rationale-drafter`), and summarizing market themes (`theme-summarizer` in Phase 2). All three are at the *edges* of the architecture — they handle input or output, but never the reasoning in between.

The reasoning in between is done by SPARQL queries against a SHACL-validated graph. Not by the LLM. This is the most important architectural decision in ATLAS.

**The alternative considered and rejected.** LLM-as-reasoner. Letting the model read raw transaction data and draw conclusions about wealth eligibility, advisor fit, or compliance risk. This is what most agentic AI demos do. It is also what makes them unauditable, non-reproducible, and structurally non-compliant with SR 11-7 and OCC 2011-12.

**The deeper reason.** Model risk regulations require that any model used in a compliance decision be documented, validated, and explainable. An LLM reasoning over arbitrary data is none of those things. A SPARQL query against a SHACL-validated graph is all three. By keeping the LLM at the edges, ATLAS makes the regulator's job possible: every decision can be traced to a deterministic query against a governed graph.

**Where the novice meets this.** Notebook `01_why_agents.ipynb` — the foundational teaching moment of Workshop 2. The novice should leave that notebook able to explain to a regulator (or to Pascal) why ATLAS is auditable.

### Thesis 4 — The four-layer permission model

Persona scoping is enforced at four layers, not one. Each layer protects against a different failure mode. No single layer would be sufficient.

| Layer | Mechanism | What it controls | What fails without it |
|---|---|---|---|
| **Identity** | AWS IAM Identity Center | Who you are and what group you belong to | Without IDC, there are no personas — just users |
| **Application** | Cognito groups federated from IDC | Which UI routes you can render | Without Cognito scoping, the Consumer Banker can navigate to the Wealth UI |
| **Data** | Lake Formation row/column filters | Which tuples your queries return | Without Lake Formation, a Consumer Banker's SPARQL query against Iceberg returns all customers, not just their assigned book |
| **Semantic** | SHACL shapes and named graphs | Which concepts and edges you can traverse | Without semantic scoping, a Consumer Banker can traverse to the BSA-restricted `SARDraft` class via a related entity |

The four layers compose. A Consumer Banker sees consumer accounts only (Data layer), with PII masked for non-owned clients (Data layer + Semantic layer), within the `:ConsumerView` named graph (Semantic layer), through a UI that doesn't render Wealth routes (Application layer), authenticated as a member of the `atlas-consumer-banker` IDC group (Identity layer).

**The alternative considered and rejected.** Single-layer enforcement. Most enterprise applications rely on application-layer permissions only — the UI hides what the user shouldn't see. This fails the moment someone calls the API directly. Lake-Formation-only enforcement fails the moment someone bypasses the federated path and queries Neptune directly. SHACL-only enforcement fails the moment someone queries the LGD instead of the SLGD.

**The deeper reason.** Defense in depth. Each layer assumes the others might fail. This is how regulated systems are built in every industry that takes audit seriously — banking, healthcare, defense. It's also how ATLAS justifies its compliance posture to the regulator: not because any one mechanism is perfect, but because no single failure exposes data.

**Where the novice meets this.** Notebook `05_wholesale_ui.ipynb` — the novice signs in as a Consumer Banker, observes one capability palette, then signs in as a BSA Analyst and observes a different one. The substrate is identical; the four layers compose to produce different views.

## How the pieces fit together

The four theses combine into a single architecture diagram. The flow of a Phase 1 referral query, end to end:

```
Consumer Banker opens Wholesale UI
                ↓
Cognito federates IDC group claim
                ↓
UI queries Agent Registry filtered by claim → returns capability palette
                ↓
UI queries AppSync GraphQL with FIBO-shaped fragment
                ↓
AppSync resolver federates:
   ├─→ Ontop on ECS Fargate → SPARQL over Neptune SLGD (Lake-Formation-scoped via Iceberg)
   ├─→ AWS Entity Resolution → canonical URI lookup
   └─→ Direct Neptune SPARQL → graph traversal
                ↓
Resolver response shaped to FIBO classes
                ↓
UI renders Entity 360 with provenance-bearing signals
                ↓
Consumer Banker clicks "Route to advisor" capability
                ↓
Capability invokes referral-orchestrator agent via Agent Registry
                ↓
Agent triggers Step Functions workflow → routing decision recorded as atlas:RoutingDecision
                ↓
Audit trail written to atlas:AuditRecord via PROV-O bindings
```

Every arrow in this flow crosses a teaching boundary. The notebooks teach each boundary in sequence. The novice builds each arrow themselves, with verification cells confirming each one works before moving to the next.

## What this architecture is not

Three things ATLAS is deliberately not, that are easy to mistake it for:

**Not a generic agentic AI platform.** ATLAS is a reference architecture for *governed agentic AI in regulated industries*. The constraints (SR 11-7, tipping-off prohibition, model risk explainability) are not optional — they shape every architectural decision. A generic agentic platform would not impose them. ATLAS does.

**Not a knowledge graph for analytics.** Workshop 1's ontology is operational, not analytical. It populates from source systems via R2RML, validates via SHACL, and serves agent queries via SPARQL. It is not designed for ad-hoc analyst exploration. (Analytical access to the underlying data goes through Iceberg directly, with the ontology as a logical overlay.)

**Not a Palantir Foundry clone.** Foundry's architectural choice is the opposite of ATLAS's: Foundry lets the LLM reason over the ontology, with proprietary controls layered on top. ATLAS keeps the LLM at the edges and uses open standards (FIBO, SHACL, R2RML, PROV-O) to draw the deterministic boundary. The trade-off is feature completeness for portability and auditability. For this posture (AWS-native, FIBO-aligned, no proprietary cloud dependency), ATLAS is the architecture; Foundry is not.

## The dependency on Workshop 1

Every thesis above depends on Workshop 1's substrate being correctly in place. Specifically:

- Thesis 1 (registry-first) depends on Workshop 1's ontology classes being the registry's vocabulary of types
- Thesis 2 (two UIs, one backbone) depends on Workshop 1's FIBO alignment being the schema's foundation
- Thesis 3 (LLM at the edges) depends on Workshop 1's SHACL shapes drawing the deterministic boundary that the LLM must not cross
- Thesis 4 (four-layer permissions) depends on Workshop 1's named graphs being the substrate of the semantic layer

If Workshop 1's substrate is incomplete, the architecture above does not work. The pre-flight notebook (`use-case-applications/notebooks/phase-1-referral/00_preflight.ipynb`) verifies every Workshop 1 dependency before any architectural component is built. See `03-data-contracts.md` for the full assertion list.

## The teaching arc

The four theses are taught in this order across Phase 1:

| Notebook | Thesis it teaches |
|---|---|
| `00_preflight` | Foundation: the Workshop 1 substrate that the four theses depend on |
| `01_why_agents` | Thesis 3 (LLM at the edges) — the regulatory heart of the architecture |
| `02_mcp_servers` | Setup for Thesis 1 (registry-first) — the capabilities being registered |
| `03_agent_registry` | Thesis 1 (registry-first) — discovery and governance |
| `04_graphql_federation` | Thesis 2 (two UIs, one backbone) — the schema that serves both |
| `05_wholesale_ui` | Thesis 4 (four-layer permissions) — visible in the rendered UI |
| `06_phase_1_acceptance` | Integration of all four theses into a working end-to-end flow |

A novice who completes Phase 1 should leave able to articulate the four theses, explain why each was chosen, and identify which Phase 1 artifact embodies each one. If they cannot do this, the workshop has built artifacts without teaching architecture — which is the failure mode this document exists to prevent.
