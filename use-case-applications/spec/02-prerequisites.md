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

### An AWS account with AgentCore preview access

**Why it matters.** Workshop 2 registers agents in AWS Agent Registry and invokes them through AgentCore Runtime. As of this writing, AgentCore is in preview and requires explicit account-level entitlement. Without it, you can build the spec but you can't run the workshop.

**How to verify.** Open the AWS console, navigate to Bedrock, and look for the AgentCore section in the left navigation. If it appears, you have access. If it doesn't, contact your AWS account team.

**The Workshop 2 teaching moment.** AgentCore is the runtime; the Agent Registry is the directory. They are separate services with separate purposes. Notebook `03_agent_registry.ipynb` is where you learn why this separation matters — registry handles discovery and governance, runtime handles invocation and observability. Most agent frameworks conflate the two; AWS keeps them apart, and the separation is what makes the four-layer permission model possible.

### Bedrock model access in your region

**Why it matters.** Three Workshop 2 agents call Bedrock foundation models. `nl-to-sparql-agent` translates natural-language questions into SPARQL. `referral-rationale-drafter` writes the narrative shown to the Consumer Banker. `theme-summarizer` (Phase 2) summarizes market themes from source articles. Without model access, these three agents fail with `AccessDeniedException` and the related notebook cells halt.

**Which models.** Workshop 2 uses Claude on Bedrock. The specific model IDs are listed in each agent's descriptor JSON. Workshop 1 already uses Claude on Bedrock for the same reason in `07_bedrock_at_edges.ipynb`, so if you completed Workshop 1, you almost certainly have what's needed.

**The Workshop 2 teaching moment.** Notebook `01_why_agents.ipynb` is where you learn why Bedrock is at the *edges* of the architecture — translating natural language to SPARQL — and not in the *middle* reasoning over data. This is the SR 11-7 / OCC 2011-12 story, and it's the most important architectural decision in ATLAS. Read that notebook before assuming you understand it from this paragraph.

### SageMaker Studio domain accessible

**Why it matters.** Workshop 2 runs from SageMaker Studio just like Workshop 1. Notebooks live in `use-case-applications/notebooks/`; you open them in Studio and execute cells. Studio is also where Kiro and Claude Code run if you choose to use either of them.

**Image choice.** The standard SageMaker Studio image (`sagemaker-distribution:cpu` or `data-science-3.0`) is sufficient. Workshop 2's `notebooks/shared/requirements.txt` lists the additional Python packages with pinned versions for reproducibility (boto3, AppSync SDK, agent registry SDK, MCP client). The first notebook installs them. Pinned versions ensure every attendee runs against the same tested dependency set regardless of when they run the workshop.

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

**The Workshop 2 teaching moment.** Notebook `05_wholesale_ui.ipynb` is where the four-layer permission model becomes visible. You sign in as the Consumer Banker, see one capability palette. You sign in as the BSA Analyst, see a different one. The substrate is identical; the difference is the IDC group claim. The novice should leave understanding which layer enforces which permission and why no single layer would be sufficient.

### Comfort with Jupyter notebooks and basic TypeScript

**Why it matters.** Workshop 2 is taught through Jupyter notebooks — same as Workshop 1. Comfort with reading and running cells is necessary. The React UI work in `06-react-monorepo/` involves TypeScript and React; you don't need senior frontend skills, but you should be able to read component code and adjust it.

**Without TypeScript comfort.** Kiro and Claude Code can generate the UI code from the spec. You read the generated code, run it, and modify it where the workshop directs. This is the recommended path for novices to frontend work.

**With TypeScript comfort.** You can adjust component code directly, customize the design, and extend the UI beyond what the spec ships. This is the recommended path for engineers building toward a POC.

## What Workshop 2's CDK stack creates

Some prerequisites are things you bring; others are things Workshop 2 creates for you. Knowing the difference prevents accidentally trying to manually create something the workshop is about to deploy.

**Workshop 2 creates (you do not):**
- Ontop on ECS Fargate (the federation runtime)
- AppSync GraphQL API and resolvers
- The five MCP server Lambdas
- Cognito user pool and IDC federation
- Lake Formation tag-based access policies
- CloudFront distributions for the two UIs
- The eight registered agents and five registered MCP servers in Agent Registry
- AgentCore Memory configuration (Phase 2)

**You provide (Workshop 2 expects):**
- Workshop 1 environment as described above
- IAM Identity Center groups as described above
- Bedrock model access as described above
- AWS Entity Resolution workflow as described above
- An AWS account with sufficient quota for the above

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

## The teaching emphasis

Each prerequisite in this document is paired with a teaching moment from the notebooks. This is intentional. Workshop 2 does not draw a line between "setup" and "learning" — the setup *is* part of the learning. Understanding why Ontop is deployed by Workshop 2 rather than Workshop 1 teaches the boundary between design artifacts and runtime infrastructure. Understanding why IDC groups must exist before the workshop starts teaches the four-layer permission model in advance of seeing it work.

If you find yourself running through this document as a checklist without absorbing the *why*, slow down. Workshop 2 is short — one to two days — but it is dense. The reading is the teaching.
