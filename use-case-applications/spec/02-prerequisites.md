# 02 — Prerequisites

This document lists what must be true about your environment before Workshop 2 begins, and explains *why* each prerequisite matters. Read the explanations — the prerequisites are not arbitrary, and understanding why each one exists is the first piece of Workshop 2's teaching.

If you are coming from Workshop 1, most of what's here is familiar. The exceptions are called out.

## The prerequisites in plain English

### A completed Workshop 1 environment

**Why it matters.** Workshop 2 does not re-teach the semantic layer. Every notebook assumes you have the ontology, the SHACL shapes, the R2RML mappings, and the populated two-tier Neptune deployment that Workshop 1 produces. If any of these are missing, Workshop 2's pre-flight notebook will refuse to start. This is intentional — Workshop 2 is the *application* of the substrate, not its construction.

**How to verify.** Run `use-case-applications/notebooks/phase-1-referral/00_preflight.ipynb`. It runs every assertion from `03-data-contracts.md` against your environment and tells you exactly what is missing if anything fails.

**What you'll see if it's wrong.** The pre-flight notebook will halt at the first failed assertion with a diagnostic message and a remediation pointer. If your Neptune cluster was torn down after Workshop 1 (which is common for cost reasons), the remediation is to redeploy from `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` and re-run Workshop 1's modules 3 and 4 to repopulate the SLGD. This takes about 90 minutes — plan accordingly.

### A persistent Neptune cluster with the SLGD populated

**Why it matters.** Workshop 2 builds agents and applications that query the Semantic Layer Graph (SLGD). The agents are stateless; the SLGD is the state. If the SLGD is empty or unreachable, every Workshop 2 demo returns empty results and every Phase 1 acceptance check fails.

**The two-tier reminder.** Workshop 1 deploys two Neptune databases: the LGD (Lexical Graph Database) for raw extracted facts, and the SLGD (Semantic Layer Graph Database) for the curated, SHACL-validated ontology. Workshop 2's agents query the SLGD by default. The LGD is used only by the Phase 2 `behavioral-signal-agent` for clickstream-derived sessions — see the Phase 2 notebooks for that distinction.

**What you'll see if it's wrong.** SPARQL queries return zero rows. Agents respond *"I couldn't find any matching customers."* The Wholesale UI's referral dashboard shows an empty state. None of this is informative on its own — the pre-flight notebook is the only place that distinguishes "empty graph" from "wrong query" cleanly.

### An AWS account with AgentCore enabled

**Why it matters.** Workshop 2 registers agents in AWS Agent Registry and invokes them through AgentCore Runtime. AgentCore reached general availability in 2026 and is available in `us-east-1` and a growing set of other regions. Workshop 2's CDK stack provisions every AgentCore resource it needs — you don't deploy AgentCore itself, but your AWS account must be in a region where it's available.

**How to verify.** Run `aws bedrock-agentcore-control list-agent-runtimes --region us-east-1`. An empty list response (`agentRuntimes: []`) confirms the service is reachable from your account. An error about the service not being available means either your account lacks permissions or you're in a region where AgentCore hasn't shipped yet. Workshop 2's pre-flight notebook runs this check automatically.

**The Workshop 2 teaching moment.** AgentCore is the runtime; the Agent Registry is the directory. They are separate services with separate purposes. Notebook `03_agent_registry.ipynb` is where you learn why this separation matters — registry handles discovery and governance, runtime handles invocation and observability. Most agent frameworks conflate the two; AWS keeps them apart, and the separation is what makes the four-layer permission model possible.

### Bedrock model access in your region

**Why it matters.** Three Workshop 2 agents call Bedrock foundation models. `nl-to-sparql-agent` translates natural-language questions into SPARQL via Titan Embeddings v2. `referral-rationale-drafter` writes the narrative shown to the Consumer Banker via Claude Sonnet. `theme-summarizer` (Phase 2) summarizes market themes via Claude Sonnet. Without model access, these three agents fail with `AccessDeniedException` and the related notebook cells halt.

**Which models.** Workshop 2 uses:
- `amazon.titan-embed-text-v2:0` (foundation model, direct invocation supported)
- `us.anthropic.claude-sonnet-4-6` (US cross-region inference profile)

**Why an inference profile rather than a bare model ID for Claude.** As of 2026, the newest Claude Sonnet models cannot be invoked on-demand via their bare foundation model IDs. AWS requires invocation through a cross-region inference profile — a wrapper that distributes requests across regions for capacity. The `us.` prefix indicates the US cross-region pool. Workshop 2 uses `us.anthropic.claude-sonnet-4-6` as the default. For customers running the workshop in a non-US AWS region, use `global.anthropic.claude-sonnet-4-6` instead by overriding the `BEDROCK_TEXT_MODEL_ID` environment variable on the relevant agents. The preflight notebook detects your region and warns you if the override is needed.

**How to verify.** Open the Bedrock console in `us-east-1` and confirm both models appear as ACTIVE. Direct invocation can be tested with `aws bedrock-runtime invoke-model --model-id 'us.anthropic.claude-sonnet-4-6' --body ...` — if this returns a response, the profile is accessible from your account.

**The Workshop 2 teaching moment.** Notebook `01_why_agents.ipynb` is where you learn why Bedrock is at the *edges* of the architecture — translating natural language to SPARQL, drafting narrative for human approval — and not in the *middle* reasoning over data. This is the SR 11-7 / OCC 2011-12 story, and it's the most important architectural decision in ATLAS. The inference profile mechanic is incidental; what matters is *what role* the LLM plays in the system.

### SageMaker Studio domain accessible

**Why it matters.** Workshop 2 runs from SageMaker Studio just like Workshop 1. Notebooks live in `use-case-applications/notebooks/`; you open them in Studio and execute cells. Studio is also where Claude Code runs if you choose to use it for code generation work in Phase 02 and beyond.

**Image choice.** The standard SageMaker Studio image (`sagemaker-distribution:cpu` or `data-science-3.0`) is sufficient. Workshop 2's `pyproject.toml` at `use-case-applications/` declares the full dependency surface; the first notebook of Phase 1 runs `uv sync --all-groups` to materialize the venv and registers the `atlas-workshop` Jupyter kernel. See "Local development environment" below for the version requirements and tooling that the venv-creation step assumes.

**Why pin everything.** Pinned versions in `pyproject.toml` (and the generated `uv.lock`) ensure every attendee runs against the same tested dependency set regardless of when they run the workshop. The exact Strands, bedrock-agentcore, rdflib, and pyshacl versions are part of the reproducibility contract.

### Ontop on ECS — deployed by Workshop 2, not Workshop 1

**Why it matters.** Workshop 1 ships R2RML mapping files but does not deploy a running Ontop service. The mappings sit in `agentic-semantic-layer/mappings/` as TTL files, waiting for a federation engine to read them. Workshop 2's CDK stack deploys Ontop on ECS Fargate and points it at those mapping files.

**Why this boundary.** Ontop is operational infrastructure — it has scaling considerations, networking concerns, and security posture that belong to the *running system*, not to the *ontology design*. Workshop 1 teaches the design; Workshop 2 deploys the runtime. Splitting the boundary this way keeps Workshop 1 portable (the mappings work with any R2RML engine) and Workshop 2 honest (the deployment is real and costs real money to run).

**The Workshop 2 teaching moment.** Notebook `04_graphql_federation.ipynb` is where you see Ontop in action. The novice should leave understanding that *federation in place* (Ontop reading from Iceberg via R2RML) and *materialization to graph* (writing triples into Neptune) are different patterns with different trade-offs. ATLAS uses both, deliberately.

### AWS Entity Resolution — verify, do not assume

**Why it matters.** Workshop 2's `atlas-er-mcp` server exposes Entity Resolution lookups: given a record from a source system, return the canonical URI that Workshop 1's ontology uses. This is how records from disparate systems converge on the same entity.

**The verification step.** Workshop 1's module 5 (`05_entity_resolution.ipynb`) walks through ER conceptually, but it does not necessarily *create* an ER workflow in your AWS account. Before starting Workshop 2, check:

1. Open the AWS Entity Resolution console.
2. Confirm a matching workflow exists named `atlas-customer-resolution` (or whatever name your Workshop 1 environment used).
3. If it does not exist, deploy it from `use-case-applications/cdk/entity-resolution.ts`.

**The Workshop 2 teaching moment.** Notebook `02_mcp_servers.ipynb` is where ER's role becomes concrete. The novice sees an MCP call return a canonical URI for a record that came in with a banking system's internal ID. The lesson is that *the URI is the contract* — once a record has a canonical URI, every other Workshop 2 agent can reason about it consistently regardless of which source system surfaced it first.

### IAM Identity Center groups for the personas

**Why it matters.** Workshop 2's four-layer permission model starts at IAM Identity Center. The personas (Consumer Banker, Wealth Advisor, BSA Analyst, Ontology Steward, Auditor) are IDC groups. Cognito federates from IDC. Lake Formation reads the IDC group claim. SHACL named graphs scope to the IDC group claim. Without IDC groups defined, the permission model collapses to "everyone sees everything."

**The five groups.** Create these as IDC groups before starting Workshop 2:

| Group | Used by |
|---|---|
| `atlas-consumer-banker` | Wholesale UI access for Phase 1 |
| `atlas-wealth-advisor` | Wealth UI access for Phase 2 |
| `atlas-bsa-analyst` | Compliance capability access (sensitive paths) |
| `atlas-ontology-steward` | Read access to the ontology and shapes |
| `atlas-auditor` | Read access to the audit trail |

Assign yourself to all five for the workshop. Production deployments would scope membership tightly.

**The Workshop 2 teaching moment.** Notebook `06_wholesale_ui.ipynb` is where the four-layer permission model becomes visible. You sign in as the Consumer Banker, see one capability palette. You sign in as the BSA Analyst, see a different one. The substrate is identical; the difference is the IDC group claim. The novice should leave understanding which layer enforces which permission and why no single layer would be sufficient.

### Comfort with Jupyter notebooks and basic TypeScript

**Why it matters.** Workshop 2 is taught through Jupyter notebooks — same as Workshop 1. Comfort with reading and running cells is necessary. The React UI work in `06-react-monorepo/` involves TypeScript and React; you don't need senior frontend skills, but you should be able to read component code and adjust it. The CDK stack at `use-case-applications/cdk/` is also TypeScript, though most attendees will not modify it directly during the workshop.

**Without TypeScript comfort.** Claude Code can generate the UI components and CDK constructs from the spec. You read the generated code, run it, and modify it where the workshop directs. This is the recommended path for novices to frontend work.

**With TypeScript comfort.** You can adjust component code directly, customize the design, and extend the UI beyond what the spec ships. You can also iterate on the CDK constructs to add resources or tune configuration. This is the recommended path for engineers building toward a POC.

### A local development environment with Python 3.12 and uv

**Why it matters.** Workshop 2's agents and notebooks require Python 3.12 or newer because Strands Agents and the bedrock-agentcore SDK both declare that as a minimum. The dependency surface is managed by `uv`, a modern Python package manager that AWS samples use throughout. If you intend to deploy the CDK stack from your own machine or run any notebook locally (rather than inside SageMaker Studio), you need this environment configured.

**What you need installed locally:**

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Agent and notebook runtime |
| uv | 0.11+ | Dependency installation and venv management |
| Node.js | 20+ | AWS CDK CLI and Claude Code |
| Docker | Any recent | Required by CDK for AgentCore Runtime asset packaging |
| AWS CLI | v2.32+ | Bedrock and IAM operations |

**How to create the venv.** From the repository root:

```
cd use-case-applications
uv sync --all-groups
```

This reads `pyproject.toml`, resolves dependencies from `uv.lock`, creates `.venv/` with Python 3.12, and installs all packages including the dev dependency group (pytest, jupyter, ipykernel, ruff). After completion, register the venv as a Jupyter kernel:

```
.venv/bin/python -m ipykernel install --user --name atlas-workshop \
    --display-name "ATLAS Workshop 2 (Python 3.12)"
```

The notebooks will then offer "ATLAS Workshop 2 (Python 3.12)" as a kernel option.

**Why uv rather than pip.** Reproducibility. The `uv.lock` file pins exact versions of all 169 transitive dependencies; every workshop attendee gets the same Python environment regardless of when they run the workshop. The same lock file works on macOS, Linux, and Windows. `pip install -r requirements.txt` is not equivalent — it resolves versions at install time, which means two attendees can get different versions of the same package.

**The Workshop 2 teaching moment.** Workshop 2 doesn't dwell on Python tooling. But the reproducibility argument is the same architectural argument as the descriptor-as-source-of-truth pattern (`04-aws-agent-registry/`) and the SHACL shapes argument (`agentic-semantic-layer/ontology/`): the artifact is the contract, and the contract is exact. Workshops that lecture about reproducibility without enforcing it end up teaching the wrong lesson.

### AWS CDK CLI v2.1102.0+ with AgentCore Runtime support

**Why it matters.** Workshop 2's CDK stack uses `agentcore.Runtime` constructs from the `@aws-cdk/aws-bedrock-agentcore-alpha` package. The CDK CLI must be at version 2.1102.0 or newer to support these constructs and the AgentCore Runtime hotswap deployment path (which speeds up Phase 02 iteration cycles dramatically — see `07-cdk-stack/README.md` for the hotswap rationale).

**How to verify and install.**

```
cdk --version
```

If the output is older than `2.1102.0`, install or upgrade:

```
npm install -g aws-cdk@latest
```

The version requirement is a moving target; AWS updates the CDK construct library regularly. Workshop 2 pins specific versions in `use-case-applications/cdk/package.json` so the construct behavior is reproducible.

**The Workshop 2 teaching moment.** The CDK construct library is itself a moving target — `@aws-cdk/aws-bedrock-agentcore-alpha` carries the alpha designation, which means construct APIs may evolve. Workshop 2 pins specific versions and re-validates against newer versions on a documented upgrade cycle. The lesson: when deploying against alpha constructs in production, version pinning is non-negotiable and upgrade cycles need to be planned, not reactive.

## What Workshop 2's CDK stack creates

Some prerequisites are things you bring; others are things Workshop 2 creates for you. Knowing the difference prevents accidentally trying to manually create something the workshop is about to deploy.

**Workshop 2 creates (you do not):**
- Ontop on ECS Fargate (the federation runtime)
- AppSync GraphQL API and resolvers
- 12 AgentCore Runtime instances (the 5 MCP servers and 7 standalone agents — every MCP-shaped component in the architecture)
- 5 Step Functions step Lambdas (internal workflow components for `referral-orchestrator`)
- 1 AgentCore Memory store (used by `conversational-context-manager`)
- Cognito user pool and IDC federation
- Lake Formation tag-based access policies
- CloudFront distributions for the two UIs
- AWS Agent Registry records (12 MCP records auto-registered by the Runtime constructs, plus 1 CUSTOM record for the `referral-orchestrator` Step Functions workflow)

**You provide (Workshop 2 expects):**
- Workshop 1 environment as described above
- IAM Identity Center groups as described above
- Bedrock model access as described above
- AWS Entity Resolution workflow as described above
- An AWS account with sufficient quota for the above
- A local development environment as described in the next section (only if you intend to run `cdk deploy` yourself or iterate on agent code)

The pre-flight notebook checks the second list. The first list is deployed by `use-case-applications/cdk/` as part of the workshop.

## Workshop Studio versus notebooks — which delivery format

Workshop 2 ships as Jupyter notebooks first. If your audience expects Workshop Studio (the AWS-hosted workshop format), the same content can be packaged that way — `use-case-applications/workshop/` is the destination, and the `contentspec.yaml` mirrors Workshop 1's structure.

**The teaching decision.** Notebooks are the better teaching format for engineers learning concepts. Workshop Studio is the better delivery format for time-bounded workshop sessions where attendees should not have to manage their own AWS environment. Both can coexist; the notebooks are the source of truth and Workshop Studio content is generated from them.

For a customer POC engagement, notebooks are preferred — the customer keeps the repository, can re-run anything, and can extend or modify as needed. For a half-day demo, Workshop Studio is preferred — attendees get a clean environment and can focus on concepts rather than setup.

## When prerequisites are not met

The pre-flight notebook is designed to fail loudly and helpfully. If any check fails, you get:

1. The exact assertion that failed
2. What the assertion was checking
3. The most likely root cause
4. The remediation steps to fix it
5. A pointer to the relevant Workshop 1 module if the gap is in Workshop 1

Do not bypass the pre-flight. Workshop 2's design assumes the contracts in `03-data-contracts.md` hold. Building on top of a partial Workshop 1 environment produces code that appears to work in development and fails opaquely in production — exactly the failure mode Workshop 2 was built to prevent.

## Set these once — the parameterization step

Workshop 2 deploys into *your* account. Nothing in this repository is wired to a
specific account: every account-specific value is supplied once, here, and flows from
there. There are three places values are set, and one two-pass step for the UI login.

### 1. CDK deploy context (`use-case-applications/cdk/cdk.json`)

The pre-flight notebook's WS1→WS2 bridge cell writes most of these automatically by
reading your Workshop 1 CloudFormation outputs. They are listed so you understand what
is set and can supply them by hand (or via `-c key=value`) if you deploy outside the
notebook:

| Context key | Source | Set by |
|---|---|---|
| `neptuneClusterEndpoint` | WS1 stack output `SLGDEndpoint` | pre-flight bridge |
| `neptuneLgdEndpoint` | WS1 stack output `LGDEndpoint` | pre-flight bridge |
| `ontologyStagingBucket` | WS1 stack output `OntologyStagingBucketName` | pre-flight bridge |
| `vpcId` | derived from the Neptune security group | pre-flight bridge |
| `privateSubnetIds` | derived from the VPC (AgentCore-supported AZs only) | pre-flight bridge |
| `runtimeArtifactsS3Prefix` | the prefix you upload runtime ZIPs under (Option C — see the pre-flight) | you, at deploy time: `-c runtimeArtifactsS3Prefix=runtimes` |
| `uiCallbackUrls` | your two CloudFront `/callback` URLs + localhost (see the two-pass step below) | you, after the first deploy |
| `cognitoDomainPrefix` | optional; defaults to `atlas-ws2-<account-id>` (globally unique per account) | auto-derived |

The committed `cdk.json` ships with **empty** values — that is correct. Do not commit
your account's values back into it.

### 2. UI environment (`apps/wholesale-ui/.env.local`, `apps/wealth-ui/.env.local`)

These files are git-ignored (they hold your account's endpoints), so a clean checkout
has none. Copy the template and fill it from your deployed stack's outputs:

```
cp apps/wholesale-ui/.env.example apps/wholesale-ui/.env.local
cp apps/wealth-ui/.env.example   apps/wealth-ui/.env.local
```

The keys (`.env.example` documents each and where it comes from):

| Var | Source (stack output) |
|---|---|
| `NEXT_PUBLIC_APPSYNC_ENDPOINT` | `AppSyncEndpoint` |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | `CognitoUserPoolWebClientId` |
| `NEXT_PUBLIC_COGNITO_DOMAIN` | `CognitoHostedUiDomain` |

Because Next.js `output: "export"` inlines `NEXT_PUBLIC_*` at build time, you must set
these *before* `next build`, and rebuild if they change.

### 3. The two-pass callback-URL step (login)

The Cognito hosted-UI OAuth flow rejects any `redirect_uri` not pre-registered on the
app client, but your CloudFront URLs are not known until the distributions exist. So
deploy in two passes:

1. **First deploy** (no `uiCallbackUrls`): creates the CloudFront distributions. Read
   their domains from the stack outputs (`WholesaleUiUrl`, `WealthUiUrl`).
2. **Redeploy** registering those callbacks:
   `npx cdk deploy -c uiCallbackUrls=https://<wholesale>/callback,https://<wealth>/callback,http://localhost:3000/callback`

Then build the UIs (step 2 above) with `NEXT_PUBLIC_COGNITO_DOMAIN` set, and sync
`out/` to the CloudFront buckets. The CDK stack does not have a hardcoded callback
default tied to any account; if you skip the `-c uiCallbackUrls=` override the client
registers only a placeholder and login will not complete until you supply your URLs.

## The teaching emphasis

Each prerequisite in this document is paired with a teaching moment from the notebooks. This is intentional. Workshop 2 does not draw a line between "setup" and "learning" — the setup *is* part of the learning. Understanding why Ontop is deployed by Workshop 2 rather than Workshop 1 teaches the boundary between design artifacts and runtime infrastructure. Understanding why IDC groups must exist before the workshop starts teaches the four-layer permission model in advance of seeing it work.

If you find yourself running through this document as a checklist without absorbing the *why*, slow down. Workshop 2 is short — one to two days — but it is dense. The reading is the teaching.
