# Workshop 1 — Building a Semantic Layer for Agentic AI

*A FIBO-aligned knowledge graph foundation for governed enterprise agents.*

## What you build

Over one day, you build an **ontology** for financial services. Not a vocabulary written in a document — a working, queryable, federated, governed ontology, hosted on Amazon Neptune, aligned to the Financial Industry Business Ontology (FIBO), and ready for AI agents to operate against.

The ontology is the centerpiece. Every other artifact in this workshop exists to populate it, validate it, federate it, or query it:

- **22 ontology classes** in two TTL files (`atlas-core.ttl` and `atlas-fibo-alignment.ttl`) — the vocabulary that defines what concepts exist in your bank's knowledge graph
- **6 SHACL boundary shapes** in `atlas-shapes.ttl` — the deterministic rules that decide what must be true for a triple to enter the graph
- **3 R2RML mappings** across three federation patterns (Iceberg, Snowflake Horizon, real-time events) — the integration layer that lets enterprise data sources participate in the ontology without bulk migration
- **A two-tier Neptune deployment** — Lexical Graph Database (LGD) for raw extracted facts, Semantic Layer Graph Database (SLGD) for the curated ontology
- **Bedrock at the edges** — natural language to SPARQL translation, the only place a language model touches the system

Together, these form the *agentic semantic layer*: a substrate that AI agents can navigate reliably, deterministically, and within model risk policy. Workshop 2 takes this substrate and builds applications on top of it.

## Why this matters

Enterprise AI agents in regulated industries cannot rely on language models alone. A model that hallucinates an account number or invents a relationship between a customer and an account is unacceptable when the answer feeds a compliance decision, a referral routing, or a wealth recommendation. The way around this is to ground the agent in a layer with explicit semantics, deterministic validation, and full provenance — an ontology.

This workshop teaches you to build that ontology in a way that maps directly to your bank's regulatory posture: every probabilistic output carries a boundary flag, every compliance-bound decision carries an explainability artifact, every triple in the graph carries provenance back to its source. The agents you build in Workshop 2 inherit all of this automatically because they operate against a graph that already enforces it.

## How you learn

This workshop is taught through eight Jupyter notebooks. Each notebook is a *narrative arc*: a question to answer, the concept that answers it, the artifact that embodies the concept, and the next question that the artifact opens. You read, you run cells, you inspect output, you understand why before you understand how.

The notebooks are designed for a novice. You do not need to know FIBO, SHACL, R2RML, or PROV-O before you start. You will know all four by the time you finish, and you will have built something with each of them.

### The eight modules

| # | Notebook | What you learn |
|---|---|---|
| 1 | `01_journey_to_ontology` | Why an ontology — and not a CRM or a data warehouse — is the right substrate for agentic AI |
| 2 | `02_fibo_alignment` | What FIBO is, why it matters, and how to extend it for concepts your bank uses that FIBO doesn't cover |
| 3 | `03_two_tier_neptune` | The LGD vs SLGD separation, and why a two-tier knowledge graph is more honest about data provenance than a single graph |
| 4 | `04_three_connection_patterns` | Pattern A (Iceberg), Pattern B (Snowflake Horizon), Pattern C (real-time) — how enterprise data flows into the ontology without bulk migration |
| 5 | `05_entity_resolution` | How AWS Entity Resolution mints canonical URIs and what to do when records don't match |
| 6 | `06_shacl_boundary` | The most important notebook in the workshop. Where the deterministic boundary lives, why SHACL draws it, and why this is the SR 11-7 / OCC 2011-12 story |
| 7 | `07_bedrock_at_edges` | Why Bedrock is at the edges of the architecture — translating natural language to SPARQL — and not in the middle reasoning over data |
| 8 | `08_wealth_signal_demo` | A worked example: surfacing a wealth-eligible customer through SHACL shapes and SPARQL CONSTRUCT queries, end to end |

Each module is roughly 45–60 minutes. The whole workshop fits a full working day.

## What you need before you start

See [`workshop/content/00-prerequisites/index.md`](./workshop/content/00-prerequisites/index.md) for the complete prerequisite list. Briefly:

- An AWS account with permissions to deploy Neptune, S3, IAM roles, and call Bedrock
- Bedrock model access enabled in your region (Claude on Bedrock)
- SageMaker Studio domain accessible
- A VPC with at least two private subnets in two different Availability Zones for the Neptune deployment (Module 3). If you already have a suitable VPC, use it; if you are starting from a clean account, build one first with **Module 0 — the foundation network** (`notebooks/00_foundation.ipynb` + `infrastructure/atlas-foundation.yaml`), which outputs the `VpcId` / `PrivateSubnetIds` / `VpcCidr` that Module 3 consumes (and bakes in the AgentCore AZ-exclusion that Workshop 2 depends on). The foundation template is dry-validated (config-verified; a full clean-account run is the live proof, tabled).
- Comfort with running cells in a Jupyter notebook

You do not need a local Python environment, local Docker, or local AWS CLI configuration. Everything runs in SageMaker Studio.

## What's in this directory

```
agentic-semantic-layer/
├── ontology/                    # The FIBO-aligned ontology — the heart of the workshop
│   ├── atlas-core.ttl           # 19 classes
│   ├── atlas-fibo-alignment.ttl # 3 FIBO-bridge classes
│   ├── atlas-shapes.ttl         # 6 SHACL boundary shapes
│   ├── extensions/              # FIBO, GLEIF, DCAT, SKOS, PROV-O bindings
│   ├── alignment-gaps.md        # Where FIBO doesn't cover what the bank needs
│   └── rationale.md             # Design decisions
├── mappings/                    # R2RML federation patterns
│   ├── pattern_a_iceberg/       # Iceberg → ontology
│   ├── pattern_b_snowflake_horizon/  # Snowflake → ontology
│   └── pattern_c_realtime/      # Real-time events → LGD
├── data/synthetic/              # 200 customers, 3,747 transactions, 10 advisors, 105 advisory relationships
├── infrastructure/              # Two-tier Neptune CloudFormation template
├── notebooks/                   # The 8 teaching modules
│   └── shared/                  # Reusable helpers — atlas_neptune, atlas_sparql, atlas_synthetic, atlas_validators
├── prompts/                     # NL→SPARQL ground truth and prefix preamble
├── docs/                        # Model risk review and runbook
└── workshop/                    # Workshop Studio content
```

## When you're done

You will have an ontology deployed on Neptune, populated with synthetic data, validated by SHACL shapes, queryable via SPARQL, and accessible via Bedrock natural language translation. You will understand why each piece exists and what changes when you add or remove it.

Then you move to [Workshop 2](../use-case-applications/), where you build agents and applications that consume what you just built.
