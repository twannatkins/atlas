# 07 — CDK Stack

The infrastructure-as-code specification for Workshop 2. A single AWS CDK v2 TypeScript stack that deploys everything Workshop 2 needs on top of Workshop 1's standing Neptune cluster.

This document explains *what* gets deployed and *why* each construct exists. Implementation lives in `use-case-applications/cdk/`. If you change a JSON descriptor in `spec/04-aws-agent-registry/`, the CDK stack must be re-synthesized — the descriptors are the source of truth for IAM policies and environment variables.

## What this stack deploys

Workshop 2's CDK stack deploys the application layer. It does **not** deploy Neptune — that is Workshop 1's infrastructure (`agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml`). The stack expects a running Neptune cluster and accepts its endpoint as a parameter.

**Why the boundary exists here.** Neptune is a shared substrate that outlives any single application. Workshop 1 deploys it because Workshop 1 owns the ontology, the SHACL shapes, and the data loading pipelines. Workshop 2 consumes it. If Workshop 2 deployed its own Neptune, you'd have two graphs, two ontologies, and zero composability — the exact failure mode Thesis 2 (two UIs, one backbone) exists to prevent.

Workshop 1's Neptune template also provisions the ontology staging bucket (SSE-S3 encrypted, public access blocked) and a scoped IAM role that grants Neptune read access to that bucket alone. The role uses an inline policy rather than a managed policy — this ensures Neptune cannot read from any other S3 bucket in the account, which matters when the same account hosts other workloads with sensitive data in S3.

## Stack parameters

| Parameter | Source | Purpose |
|---|---|---|
| `neptuneClusterEndpoint` | Workshop 1 CFN output | SLGD/LGD read/write endpoint |
| `neptuneClusterArn` | Workshop 1 CFN output | IAM policy resource scope |
| `vpcId` | Workshop 1 CFN output | Shared VPC for Neptune connectivity |
| `privateSubnetIds` | Workshop 1 CFN output | Subnets with Neptune route |

## Construct map

The stack is organized as nested constructs. Each construct owns a single concern.

### 1. Networking construct

**What.** A NAT gateway in the existing VPC's public subnets, plus security groups for Lambda-to-Neptune and ECS-to-Neptune traffic.

**Why.** Lambda functions in private subnets need outbound internet for Bedrock API calls (the LLM-at-the-edges pattern). Neptune access requires private subnet placement. NAT bridges both requirements. The VPC itself is not created here — it belongs to Workshop 1. We add only the NAT gateway and the security group rules Workshop 2 needs.

**Egress scoping.** Security groups use explicit egress rules rather than `allowAllOutbound`. Lambda functions can reach Neptune (8182), Ontop (8080), and HTTPS (443 for Bedrock and AWS APIs). ECS tasks can reach Neptune (8182) and HTTPS (443 for ECR image pulls). No other outbound traffic is permitted — this limits the blast radius if a workload is compromised.

**Why not a VPC endpoint for Bedrock?** VPC endpoints for Bedrock are region-limited and don't cover all model invocation paths. NAT is the reliable path today. When Bedrock VPC endpoints reach GA in all target regions, this construct should be updated.

### 2. Ontop on ECS Fargate

**What.** An ECS Fargate service running the Ontop SPARQL-over-relational translation layer. Sits in private subnets with Neptune access. Exposes an internal ALB endpoint consumed by `atlas-sparql-mcp`. When a `certificateArn` is provided, the ALB uses HTTPS to encrypt SPARQL queries in transit; without one (local development), it falls back to HTTP on the internal network.

**Why.** Ontop translates SPARQL queries into SQL against Lake Formation Iceberg tables. This is how Workshop 2 federates relational data into the knowledge graph without materializing triples. The alternative — bulk-loading relational data into Neptune — violates the "single source of truth" principle and creates a stale-data problem that no ETL schedule solves.

**Why Fargate, not Lambda?** Ontop maintains an in-memory R2RML mapping cache and a JDBC connection pool. Cold starts would be 8–12 seconds. Fargate keeps the service warm with a minimum task count of 1. Cost is ~$15/month for the workshop's synthetic data scale.

### 3. Cognito User Pool + IDC federation

**What.** A Cognito User Pool federated from AWS IAM Identity Center. Five groups corresponding to the five ATLAS personas:

| Cognito group | IDC group | Role in Workshop 2 |
|---|---|---|
| `atlas-consumer-banker` | Same | Wholesale UI access; sees consumer book only |
| `atlas-wealth-advisor` | Same | Wealth UI access; sees assigned clients only |
| `atlas-bsa-analyst` | Same | BSA routes in both UIs; sees SAR-eligible data |
| `atlas-ontology-steward` | Same | Admin routes; can modify ontology extensions |
| `atlas-auditor` | Same | Read-only audit trail access across all UIs |

**Why Cognito and not IDC alone?** IDC handles *identity* (who you are). Cognito handles *application-layer permissions* (what UI routes you can render, what Agent Registry capabilities you see). This is Layer 2 of the four-layer permission model from `01-architecture.md`. Without Cognito, the UI would need to parse raw IDC SAML assertions to determine group membership — fragile, non-standard, and untestable in local development.

**How the persona flows.** The client sends only the Cognito JWT in the Authorization header. AppSync validates the token and extracts the `cognito:groups` claim server-side — the persona is never sent as a client-supplied header. This prevents privilege escalation via localStorage manipulation. The resolver passes the server-extracted persona to the MCP servers for Lake Formation scoping.

**Why federate rather than manage users directly in Cognito?** Because the enterprise already has IDC. Duplicating user management in Cognito creates identity drift. Federation means a single source of truth for group membership, with Cognito as the application-facing token issuer.

### 4. AppSync GraphQL API

**What.** An AWS AppSync API whose schema is read from `spec/05-appsync-graphql/schema.graphql`. Resolvers federate across Neptune (direct SPARQL), Ontop (SPARQL-over-relational), and AWS Entity Resolution.

**Why AppSync and not a custom GraphQL server?** AppSync gives us Cognito integration (authorization by group claim), resolver-level caching, and subscription support for real-time signal updates — all without managing a server. The schema is FIBO-shaped, meaning the GraphQL types mirror FIBO classes. This is what makes Thesis 2 (two UIs, one backbone) work: both UIs query the same FIBO-shaped schema with different persona claims, and the resolvers return persona-scoped results.

### 5. Lambda deployments (13 handlers)

**What.** Thirteen Lambda functions: 5 MCP servers and 8 agents. Each is deployed from its source directory under `use-case-applications/mcp-servers/` or `use-case-applications/agents/`.

**MCP servers (5):**
- `atlas-sparql-mcp` — SPARQL query/update over Neptune
- `atlas-shacl-mcp` — SHACL validation
- `atlas-fibo-mcp` — FIBO class/property lookup
- `atlas-er-mcp` — Entity Resolution canonical URI lookup
- `atlas-registry-mcp` — Agent Registry query interface

**Agents (8):**
- `wealth-signal-detector` — Fires wealth signals via SPARQL CONSTRUCT
- `household-traverser` — Graph traversal for household membership
- `nl-to-sparql-agent` — Natural language to SPARQL translation (Bedrock)
- `referral-rationale-drafter` — Narrative generation for referral rationale (Bedrock)
- `referral-orchestrator` — Step Functions workflow trigger (see construct 7)
- `behavioral-signal-agent` — Session/network signals (Phase 2)
- `conversational-context-manager` — AgentCore Memory session state (Phase 2)
- `theme-summarizer` — Market theme summarization (Phase 2, Bedrock)

**How IAM policies are assigned.** Each Lambda's inline IAM policy is read directly from its JSON descriptor in `spec/04-aws-agent-registry/`. The CDK stack parses the `iam_policy.inline_policy` field and attaches it to the Lambda's execution role. No policy is hand-written in CDK code — the descriptors are the single source of truth.

**How environment variables are assigned.** Each Lambda's environment variables are read from the `runtime.environment_variables` field in its JSON descriptor. Placeholder tokens like `${slgd_endpoint}` and `${neptune_cluster_arn}` are resolved to CDK token references at synth time. This means a descriptor change propagates to the deployed Lambda on the next `cdk deploy` without touching CDK code.

**Why this pattern?** Governance. The JSON descriptors are reviewed by the platform team and committed alongside the agent's MRM documentation. If IAM policies lived only in CDK code, the security review would require reading TypeScript infrastructure code — a different skill set from reviewing a declarative policy document. The descriptor-as-source-of-truth pattern keeps the security review in JSON, where auditors can read it.

### 6. CloudFront distributions

**What.** Two CloudFront distributions serving the React SPAs:
- `wholesale-ui` — Consumer Banker referral interface (Phase 1)
- `wealth-ui` — Wealth Advisor workbench (Phase 2)

Each distribution fronts an S3 origin bucket. The React build artifacts are deployed to S3 by the CI pipeline; the CDK stack creates the bucket, the distribution, and the OAC (Origin Access Control).

**Why CloudFront and not AppSync hosting?** The UIs are static React SPAs that call AppSync via the Amplify client. They don't need server-side rendering. CloudFront gives us edge caching, custom domain support, and WAF integration — none of which AppSync hosting provides for static assets.

### 7. Step Functions state machine

**What.** A single state machine for the `referral-orchestrator` workflow. Five steps, each invoking a dedicated Lambda:

```
select-advisor → validate-routing → write-routing-decision → notify-advisor → audit-write
```

**Why Step Functions and not Lambda-to-Lambda chaining?** Auditability. Step Functions provides a visual execution history, automatic retry with backoff, and a durable execution record. When the auditor asks "what happened to referral X?", the answer is a Step Functions execution ARN with a complete state transition log. Lambda-to-Lambda chaining provides none of this — failures are silent, retries are manual, and there is no execution record unless you build one yourself.

**Why five steps and not one monolithic Lambda?** Each step has a different failure mode and a different retry policy. `select-advisor` might fail because no advisor has capacity (retry with expanded criteria). `validate-routing` might fail because SHACL validation rejects the routing decision (no retry — surface to human). `audit-write` must succeed even if earlier steps partially failed (compensating transaction). Separating steps lets each one own its failure semantics.

### 8. Lake Formation tag policies

**What.** LF-Tag policies that scope data access by persona. Tags are applied to Iceberg table columns and rows; policies grant access based on the Cognito group claim passed through the query path.

| Tag | Values | Effect |
|---|---|---|
| `atlas:persona` | `consumer-banker`, `wealth-advisor`, `bsa-analyst`, `ontology-steward`, `auditor` | Row-level: restricts which customers a query returns |
| `atlas:sensitivity` | `public`, `pii`, `sar-restricted` | Column-level: masks PII columns for non-owning personas |

**Why Lake Formation and not Neptune-level access control?** Neptune's IAM-based access control operates at the cluster level — you can grant or deny access to the entire database, but not to individual triples or named graphs. Lake Formation operates at the row and column level on the Iceberg tables that Ontop federates. This is Layer 3 (Data layer) of the four-layer permission model. Without it, a Consumer Banker's SPARQL query through Ontop would return all customers, not just their assigned book.

**The regulatory driver.** OCC 2011-12 requires that model inputs be traceable to authorized data. If a wealth signal fires on a customer outside the banker's book, the signal is both a data breach and an unauditable model input. Lake Formation tag policies prevent this structurally — the query never sees the unauthorized rows.

## What the stack does NOT deploy

| Resource | Owner | Why not here |
|---|---|---|
| Neptune cluster | Workshop 1 CFN | Shared substrate; outlives applications |
| IAM Identity Center | Organization admin | Pre-existing enterprise identity |
| Bedrock model access | Account-level setting | Not deployable via CDK |
| Agent Registry | AWS managed service | No deployment needed; API-only |
| Iceberg tables | Workshop 1 data pipeline | Data layer owned by data engineering |

## Synthesis and deployment

```bash
cd use-case-applications/cdk
npx cdk synth --context neptuneClusterEndpoint=<endpoint> \
              --context neptuneClusterArn=<arn> \
              --context vpcId=<vpc-id> \
              --context privateSubnetIds=<subnet-1,subnet-2>
npx cdk deploy
```

The stack is a single CloudFormation stack (not multiple stacks) because all constructs share the VPC, the Cognito pool, and cross-references between Lambda ARNs. Splitting into multiple stacks would require export/import for every cross-reference — added complexity with no isolation benefit at workshop scale.

## Teaching note

The CDK stack is deployed once at the start of Phase 1, before the first notebook runs. The notebooks do not deploy infrastructure — they consume it. This separation is deliberate: the novice should understand that infrastructure and application logic are different concerns with different change cadences, different review processes, and different blast radii. A notebook that deploys a Lambda on every run is teaching the wrong lesson about production operations.
