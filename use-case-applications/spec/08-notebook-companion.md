# 08 — Notebook Companion

The Workshop 2 notebooks are the primary teaching mechanism. Each notebook is a *narrative arc*, not a build script: a question to answer, the concept that answers it, the artifact that embodies the concept, and the next question that the artifact opens.

This is the same structure Workshop 1 uses. A novice running the notebooks should leave understanding *why* each piece of agentic AI infrastructure exists, not just *how* to deploy it.

## Teaching principles

Every notebook in Workshop 2 follows the same five-section pattern. Cells are organized this way so that a novice can read, understand, build, and verify in a continuous flow.

### Section 1 — The question

Each notebook opens with a concrete question that a novice would naturally ask at that point in the journey. Examples:

- "If Workshop 1 already gave me a knowledge graph and SPARQL, why do I need agents at all?"
- "What does an Agent Registry actually solve that I couldn't solve with Lambda and DynamoDB?"
- "Why does the Wholesale UI's compliance banner say 'Active compliance review' instead of 'SAR filed'?"

The question frames why what follows is worth your time. If the novice can't see the question as theirs, the notebook has not earned the right to teach them the answer.

### Section 2 — The concept

A short narrative — three to six paragraphs — that explains the concept the notebook will build. No code. No AWS service names except where they are unavoidable for clarity. The novice should be able to read this section, close the laptop, and explain the idea to a colleague.

Where the concept is regulatory, the explanation includes the regulation in plain English. *"31 U.S.C. §5318(g)(2) makes it a federal crime to disclose to anyone outside the BSA function that a SAR has been filed. This is called tipping-off. The UI banner cannot say 'SAR filed' because the banner is visible to a Consumer Banker, and a Consumer Banker is outside the BSA function. The banner says 'Active compliance review' because that is what the Consumer Banker is allowed to know."*

The concept section is the heart of the notebook. Skip the rest if you must; read this every time.

### Section 3 — The build

Code cells that produce the artifact. Each cell is preceded by a brief comment that connects it to the concept. Build cells are intentionally small — never more than 20 lines of code per cell — so that a novice can pause between them and inspect intermediate state.

Where the build calls an AWS service, the cell includes a comment explaining *which* service is being called and *why*. Where the build uses a Workshop 1 artifact (a SHACL shape, a SPARQL prefix, a synthetic data row), the comment names the artifact explicitly.

### Section 4 — The verification

Cells that prove the artifact works. Verification cells are inspectable — they print the response, they show the registered record, they run a test query — rather than just asserting success. A novice should be able to look at the output and understand what changed in the world.

Verification cells are also where errors are caught. Each verification cell includes a remediation comment that tells the novice what to do if the cell fails: *"If this cell raises `AccessDeniedException`, the most likely cause is that Bedrock model access is not enabled in this region. See `02-prerequisites.md` for the model access checklist."*

### Section 5 — What just changed

The closing section of every notebook. Three to five sentences that summarize what the novice now has that they did not have before, and what becomes possible next. This is the bridge to the next notebook.

## The Phase 1 notebooks (Consumer-to-Wealth Referral)

Six notebooks. Each takes 45–60 minutes for a novice working at a comfortable pace. The whole phase fits a working day.

### `00_preflight.ipynb` — Are we ready?

**Question:** How do I know my Workshop 1 environment is complete enough for Workshop 2 to start?

**Concept:** Workshop 2 inherits 22 ontology classes, 6 SHACL shapes, 3 R2RML mappings, and a populated two-tier Neptune deployment from Workshop 1. The pre-flight notebook does not build anything — it verifies that what Workshop 2 expects to find is actually there. If anything is missing, this notebook tells you exactly what and how to fix it before you proceed.

**Build:** None. This notebook is verification only.

**Verification:** The Python assertions defined in `03-data-contracts.md` — class count, shape names, data row counts, file paths, Bedrock model access, Neptune connectivity. Each assertion has a corresponding remediation guide.

**What just changed:** You have confirmed that Workshop 1's substrate is in the state Workshop 2 expects. Workshop 2 is now safe to start.

### `01_why_agents.ipynb` — Why agents at all?

**Question:** Workshop 1 gave me a knowledge graph and SPARQL queries. Why do I need agents?

**Concept:** A SPARQL query is a deterministic transformation of a question into a graph traversal. But a banker doesn't speak SPARQL — they speak business questions like *"is this customer wealth-eligible?"* An agent's job is to translate business questions into graph operations and back, *without* itself becoming the place where business logic lives. The agent is an interface, not a reasoner. This is the most important distinction in Workshop 2 — and it is what makes ATLAS compliant with SR 11-7 and OCC 2011-12.

A novice should leave this notebook understanding the difference between *LLM-as-interface* and *LLM-as-reasoner*, why the former is auditable and the latter is not, and why every agent in ATLAS is the former.

**Build:** Walk through a single SPARQL query against the SLGD using the `atlas_sparql` helper from Workshop 1. Then call the same query through a wrapped pattern that mimics what an agent will do: receive a natural-language question, look up the matching SPARQL in the ground-truth set, execute it, return the result. No registry yet, no MCP servers yet — just the pattern.

**Verification:** Run three natural-language questions through the pattern. Inspect the SPARQL each one produces. Confirm that the SPARQL is deterministic — the same input produces the same query every time.

**What just changed:** You have seen the pattern that agents implement. The rest of Phase 1 is making this pattern multi-agent, discoverable, governable, and surfaced through a UI.

### `02_mcp_servers.ipynb` — Why MCP servers?

**Question:** Why do agents talk to MCP servers instead of directly to AWS services?

**Concept:** An MCP (Model Context Protocol) server is a stable, typed interface that an agent can call regardless of what's behind it. The agent doesn't need to know whether SPARQL queries hit Neptune directly, hit Ontop, hit a cached materialization, or hit a real-time stream. The agent just calls `atlas-sparql-mcp.query(...)` and gets results. This indirection is what makes ATLAS evolvable — the agents from Phase 1 keep working when the data layer changes in Phase 2.

The five MCP servers in Workshop 2 each wrap one capability: SPARQL, SHACL validation, Entity Resolution lookup, FIBO class introspection, and registry discovery itself. Together, they form the *capability surface* agents operate against.

**Build:** Implement and deploy the five MCP server Lambdas using the descriptors in `04-aws-agent-registry/`. Each is a thin wrapper around an AWS service.

**Verification:** Call each MCP server directly. Inspect the response. Confirm that the schema matches the descriptor.

**What just changed:** Workshop 2 now has a capability surface. The next notebook makes it discoverable.

### `03_agent_registry.ipynb` — Why a registry?

**Question:** If MCP servers are just Lambdas, why do I need an Agent Registry?

**Concept:** A registry solves two problems that grow in importance as the number of agents grows. First, *discovery*: a UI doesn't want to hardcode which agents exist — it wants to ask the registry "what can I show this user?" and render whatever comes back. Second, *governance*: an organization needs an approval workflow for new agents, because every registered agent is a new attack surface and a new MRM submission. The Agent Registry is both a directory and a gate.

Workshop 2 uses AWS Agent Registry with IAM-based authorization in Phase 1 and switches to JWT-based authorization in Phase 2. The reason for the switch is itself a teaching moment — see notebook `phase-2-advisor/04_jwt_auth.ipynb`.

**Build:** Register the five MCP servers from the previous notebook. Register the five Phase 1 agents (`nl-to-sparql-agent`, `wealth-signal-detector`, `referral-rationale-drafter`, `household-traverser`, `referral-orchestrator`). Walk through the approval workflow for each.

**Verification:** Query the registry as a Consumer Banker and confirm that the discoverable set matches what Phase 1 expects. Query it as a Wealth Advisor and confirm that the set is different — discovery is persona-scoped from the start, not bolted on later.

**What just changed:** Agents and MCP servers are discoverable. The UI can now ask the registry what to render.

### `04_graphql_federation.ipynb` — Why AppSync, why FIBO-shaped?

**Question:** Why does the UI talk to GraphQL instead of calling agents directly?

**Concept:** Two reasons. First, the UI needs a *shape* — a schema it can write components against. GraphQL provides this; agent calls do not. Second, the schema being FIBO-shaped is what makes the UI legible to anyone who knows FIBO. A developer writing a new screen doesn't need to know which agent to call — they write a GraphQL fragment against `fibo:Party.advisoryRelationship`, and the resolver behind it figures out whether to call SPARQL, Entity Resolution, or a federated Iceberg table.

This is also the place where the ontology becomes a contract that crosses team boundaries. The frontend team writes against FIBO classes. The backend team implements resolvers that produce instances of FIBO classes. The two teams can work independently because the schema is the agreement.

**Build:** Deploy the FIBO-shaped GraphQL schema via CDK. Wire the resolvers — some federate to Ontop (Neptune via SPARQL), some to AWS Entity Resolution, some to Iceberg tables via Athena.

**Verification:** Execute three GraphQL queries that exercise three different resolver paths. Inspect the resolved data. Confirm that the GraphQL response shape conforms to the FIBO classes declared in the schema.

**What just changed:** Workshop 2 now has a FIBO-shaped API. The next notebook puts a UI on top of it.

### `06_wholesale_ui.ipynb` — Wiring the Wholesale UI

**Question:** How does a React app consume registered agents and a FIBO-shaped API together?

**Concept:** The Wholesale UI demonstrates the *two-driver architecture* of an agentic AI application: the GraphQL API drives *what data is rendered*, and the Agent Registry drives *what actions are available*. The same Referral Detail screen rendered for a Consumer Banker and a BSA Analyst shows similar data but different capability palettes — because the registry filters discoverable capabilities by persona claim.

This is the place where the four-layer permission model (IAM Identity Center → Cognito → Lake Formation → SHACL named graphs) becomes visible to the user. The novice should leave understanding which layer enforces which permission and why.

**Build:** Deploy the Wholesale UI via CDK to CloudFront with Cognito sign-in. Sign in as Rachel Kim (Consumer Banker). Open the Patel household referral. Observe the capability palette populating live from the registry, the wealth-readiness signals rendering with provenance, and the compliance banner reading *"Active compliance review — contact BSA team."*

**Verification:** Sign in as a non-Consumer-Banker persona (Wealth Advisor) and confirm that the same screen renders differently — different capabilities, different signal access, different compliance posture. The UI is one codebase; the differences come from the persona claim.

**What just changed:** Workshop 2 has a working application. The substrate from Workshop 1 is now serving a real banking use case end to end. Phase 1 is complete.

### `07_phase_1_acceptance.ipynb` — Did everything land?

**Question:** Before I move to Phase 2, how do I know Phase 1 is actually complete?

**Concept:** Phase 1 acceptance is the moment Workshop 2 becomes more than a demo. Every assertion in `10-acceptance-criteria.md` is a contract: if all of them pass, you have a working Phase 1 that you can hand to a customer. If any fail, you have a known issue to address before extending to Phase 2.

**Build:** None.

**Verification:** Run every assertion in `10-acceptance-criteria.md` for Phase 1. The Rachel Kim end-to-end scenario, the four permission layers, the registry discovery scoping, the audit trail completeness, the FIBO conformance of the GraphQL responses.

**What just changed:** You have a Phase 1 that meets every contract in the spec. The next phase is optional today, recommended self-paced.

## The Phase 2 notebooks (Wealth Advisor Spine)

Six more notebooks, same structure. Phase 2 introduces AgentCore Memory, JWT-based registry authorization, the Wealth UI, and three additional agents (`behavioral-signal-agent`, `theme-summarizer`, `conversational-context-manager`).

| # | Notebook | Question it answers |
|---|---|---|
| 1 | `01_phase_2_agents` | Why does Phase 2 need different agents than Phase 1? |
| 2 | `02_agentcore_memory` | What changes when an agent can remember context across invocations? |
| 3 | `03_wealth_ui` | How does the same backbone serve a structurally different application? |
| 4 | `04_jwt_auth` | Why switch the registry from IAM to JWT, and what does it enable? |
| 5 | `05_end_to_end` | Walk the advisor scenario across both UIs |
| 6 | `06_phase_2_acceptance` | Final acceptance — does the two-UI thesis hold? |

Each follows the question → concept → build → verification → what-just-changed pattern. Detail in the individual notebook designs under `08-notebook-companion/phase-2/`.

## Why this structure matters

The audience for Workshop 2 is "a novice to agentic AI tooling." A novice does not learn by running cells that pass. A novice learns by understanding *why* each cell exists, *what* it changes about the world, and *what* opens up next. The five-section pattern is how each notebook teaches, not just builds.

This is also why the notebooks are the primary teaching mechanism rather than the spec. The spec is for Kiro and Claude Code to read when generating production artifacts. The notebooks are for humans to read when learning. Both audiences are necessary; they are served by different documents.
