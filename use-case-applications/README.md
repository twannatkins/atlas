# Workshop 2 — Use Case Applications

*Two governed banking applications built on the Workshop 1 semantic layer.*

## What you build

Workshop 1 produced a FIBO-aligned ontology on a two-tier Neptune deployment. Workshop 2 takes that substrate and builds two real banking applications on top of it — without modifying anything Workshop 1 produced. Every Workshop 2 extension lives in the `atlas-part-2:` namespace; the Workshop 1 ontology, shapes, and data are read, never altered.

The deliverables:

- **Two Next.js 18 applications** in `apps/` — the **Wholesale UI** (a Consumer Banker's referral workbench) and the **Wealth UI** (a Wealth Advisor's coverage and conversation workbench). Both consume the same GraphQL API and drive their action palettes from a live registry query rather than hardcoded buttons.
- **Eight agents** in `agents/` — five Phase 1 referral agents (`nl-to-sparql-agent`, `wealth-signal-detector`, `household-traverser`, `referral-rationale-drafter`, `referral-orchestrator`) and three Phase 2 advisor agents (`behavioral-signal-agent`, `conversational-context-manager`, `theme-summarizer`), each with a JSON descriptor in `spec/04-aws-agent-registry/agents/`.
- **Five MCP servers** in `mcp-servers/` — SPARQL, SHACL validation, Entity Resolution, FIBO introspection, and registry discovery — the capability surface every agent operates against, deployed as AgentCore Runtimes.
- **A FIBO-shaped GraphQL API** — an AppSync schema where every type maps to an ontology class, served by three resolver patterns (`appsync-resolvers/`): SPARQL via Ontop over Iceberg, direct Neptune SPARQL, and Entity Resolution.
- **A CDK stack** in `cdk/` — the full infrastructure: AgentCore runtimes and memory, AppSync, Cognito, Lake Formation, Ontop on ECS, CloudFront, Step Functions, and networking.
- **Thirteen teaching notebooks** in `notebooks/` — the primary way you learn what each piece does and why.

The agents, MCP servers, resolvers, and UIs are all implemented in this repository. The notebooks build and verify the architecture through local simulation; deploying it to live AWS — standing up the UIs, the GraphQL endpoint, and the registered runtimes against a real Neptune cluster — is the CDK deployment step, run against your own account.

## Why this matters

Workshop 1 made the case that agentic AI in a regulated bank needs a governed substrate — an ontology with deterministic validation and full provenance — rather than a language model reasoning over raw data. Workshop 2 proves that case by building on it. The agents here do not reason; they translate business questions into graph operations against the SHACL-validated graph and return auditable results. Bedrock is called only for natural-language translation and narrative drafting, never for the decisions themselves.

Two architectural theses drive the workshop. **Thesis 1 (Phase 1): registry-first discovery** — a UI never hardcodes what agents exist; it asks the registry, which answers based on the caller's persona. **Thesis 2 (Phase 2): two UIs, one backbone** — two structurally different applications consume the same schema, registry, and MCP servers, differing only in which fragments they query and which persona they claim. Together they show an architecture that scales by addition — new UIs, new personas — rather than modification.

## How you learn

Workshop 2 is taught through thirteen Jupyter notebooks in two phases, each following the same narrative arc as Workshop 1: a question, the concept that answers it, the artifact that embodies it, the verification that proves it, and the bridge to the next question. The notebooks are designed for a novice to agentic AI tooling — you read the concept, run the cells, inspect the output, and understand why before how.

The notebooks run as local simulations of the deployed services, so you can work through the entire architecture before deploying anything. The corresponding Workshop Studio pages live in `workshop/content/` and frame each notebook for instructor-led or self-paced delivery.

### Phase 1 — Consumer-to-Wealth Referral

| # | Notebook | What you learn |
|---|---|---|
| 1 | `00_preflight` | Verify the Workshop 1 substrate is present and in the state Workshop 2 expects |
| 2 | `01_why_agents` | The agent pattern: cosine-similarity NL-to-SPARQL template selection, and why determinism is the SR 11-7 story |
| 3 | `02_mcp_servers` | The MCP server contract, and why production runtimes are AgentCore Runtimes behind a stable interface |
| 4 | `03_agent_registry` | Registry-governed discovery and persona-scoped capability palettes (Thesis 1) |
| 5 | `04_graphql_federation` | The FIBO-shaped GraphQL schema and its three resolver patterns |
| 6 | `05_wealth_signals` | How wealth signals are derived (not inserted): the Large Deposit Pattern and No Advisor Coverage derivations, validate-before-write, and why an unsupported third signal is honestly refused |
| 7 | `06_wholesale_ui` | The two-driver architecture, and the tipping-off prohibition (31 U.S.C. §5318(g)(2)) that governs the compliance banner |
| 8 | `07_phase_1_acceptance` | The Phase 1 acceptance suite — 36 assertions across seven categories |

### Phase 2 — Wealth Advisor Spine

| # | Notebook | What you learn |
|---|---|---|
| 8 | `01_phase_2_agents` | Why behavioral signals need a different agent: LGD tier, probabilistic-guarded posture |
| 9 | `02_agentcore_memory` | Session-scoped memory and multi-turn context resolution — and why it is session-scoped by compliance design |
| 10 | `03_wealth_ui` | Thesis 2: the same backbone serving a structurally different application |
| 11 | `04_jwt_auth` | The shift from IAM to JWT: the persona claim moves into a Cognito-signed token |
| 12 | `05_end_to_end` | The cross-UI advisor flow and the audit trail spanning both personas |
| 13 | `06_phase_2_acceptance` | The Phase 2 acceptance suite — 20 assertions across five categories, validating Thesis 2 |

Phase 1 is roughly a full working day; Phase 2 is a self-paced extension.

## What you need before you start

See [`workshop/content/00-prerequisites/index.md`](./workshop/content/00-prerequisites/index.md) for the complete list. Briefly:

- **Workshop 1 complete** — the pre-flight notebook (Module 1) verifies its ontology, SHACL shapes, and populated Neptune are present and refuses to start without them
- **The Workshop 2 Python environment** — `uv sync --all-groups` from this directory, then register the `atlas-workshop` Jupyter kernel
- **Bedrock model access** — Amazon Titan Embeddings v2 and Claude Sonnet via the US cross-region inference profile (`us.anthropic.claude-sonnet-4-6`)
- **AgentCore available in your region** (us-east-1), and the AWS CDK CLI for the deployment step

The notebooks run locally against simulations; the CDK deployment step is what requires the full AWS environment.

## What's in this directory

```
use-case-applications/
├── agents/                      # Eight agent implementations
│   ├── nl-to-sparql-agent/      # Cosine-similarity NL→SPARQL; deterministic-audited posture
│   ├── wealth-signal-detector/  # SHACL-validated signal detection
│   ├── household-traverser/     # Household graph traversal
│   ├── referral-rationale-drafter/  # Bedrock narrative drafting; probabilistic-guarded
│   ├── referral-orchestrator/   # Human-in-the-loop routing; requires approved_rationale
│   ├── behavioral-signal-agent/ # EngagementDecay and NetworkInfluence via LGD
│   ├── conversational-context-manager/  # Session-scoped memory; multi-turn context
│   └── theme-summarizer/        # Market theme summaries; Wealth Advisor only
├── mcp-servers/                 # Five MCP server handlers (AgentCore Runtimes)
│   ├── atlas-sparql-mcp/        # SPARQL over Neptune; validates persona (LF row-scoping is roadmap)
│   ├── atlas-shacl-mcp/         # SHACL shape validation
│   ├── atlas-er-mcp/            # Entity Resolution identity lookup
│   ├── atlas-fibo-mcp/          # FIBO class introspection
│   └── atlas-registry-mcp/      # Agent registry discovery
├── apps/                        # Two Next.js 18 applications
│   ├── wholesale-ui/            # Consumer Banker referral workbench
│   ├── wealth-ui/               # Wealth Advisor coverage and conversation workbench
│   └── shared/                  # Shared auth, GraphQL client, UI primitives
├── appsync-resolvers/           # Three AppSync Lambda resolvers with tests
│   ├── sparql-resolver/         # Ontop/SPARQL resolver for entity data
│   ├── er-resolver/             # Entity Resolution resolver
│   └── registry-resolver/       # Agent registry capabilities resolver
├── cdk/                         # CDK TypeScript stack
│   └── lib/constructs/          # AgentCore, AppSync, Cognito, CloudFront, Lake Formation, Ontop, Step Functions
├── notebooks/                   # Thirteen teaching notebooks
│   ├── phase-1-referral/        # 00_preflight through 07_phase_1_acceptance
│   └── phase-2-advisor/         # 01_phase_2_agents through 06_phase_2_acceptance
├── ontology-extensions/         # atlas-part-2: namespace TTL files
│   ├── behavioral.ttl           # EngagementDecay, NetworkInfluence signal classes
│   ├── referrals.ttl            # Referral workflow classes
│   ├── signal-types.ttl         # Extended signal type vocabulary
│   └── themes.ttl               # Market theme classes
├── spec/                        # Architecture and contract documentation
│   ├── 03-data-contracts.md     # What Workshop 2 inherits from Workshop 1 (verified by pre-flight)
│   ├── 04-aws-agent-registry/   # Agent and MCP server JSON descriptors
│   ├── 05-appsync-graphql/      # GraphQL schema and resolver specs
│   ├── 06-react-monorepo/       # UI component and route specs
│   ├── 07-cdk-stack/            # Infrastructure spec
│   └── 10-acceptance-criteria.md  # Phase 1 acceptance assertions (36 across 7 categories)
├── prompts/                     # Rationale template and SPARQL signal queries
├── workshop/                    # Workshop Studio content (15 pages, contentspec.yaml)
├── CLAUDE.md                    # Build directives for Claude Code
└── pyproject.toml               # Python project — managed by uv
```

## When you're done

You will have worked through every notebook in both phases, verified all acceptance assertions locally, and seen the full referral workflow simulated from signal detection to cross-UI audit trail. When the CDK stack is deployed, the nine assertions in Module 7 that require a live Neptune cluster (Category 5's end-to-end checks and Category 3's row-filter checks) can be run against the real environment to confirm the production behavior matches the local simulation.

Then you have a working, governed, agent-driven application stack: two UIs, eight agents, five MCP servers, a FIBO-shaped API, and a complete audit trail from signal to advisor action. Adapt it to a new use case by adding agents and persona claims — the backbone does not change.
