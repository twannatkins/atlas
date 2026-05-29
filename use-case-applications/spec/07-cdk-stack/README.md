# 07 — CDK Stack

The infrastructure-as-code specification for Workshop 2. A single AWS CDK v2 TypeScript stack that deploys Workshop 2's application layer on top of Workshop 1's standing Neptune cluster, with Amazon Bedrock AgentCore as the runtime substrate for the 12 MCP-shaped components.

This document explains *what* gets deployed and *why* each construct exists. Implementation lives in `use-case-applications/cdk/`. If you change a JSON descriptor in `spec/04-aws-agent-registry/`, the CDK stack must be re-synthesized — the descriptors are the source of truth for IAM policies and environment variables.

## AgentCore CDK packages

The stack depends on two CDK packages for AgentCore primitives:

- **`aws-cdk-lib`** (stable) — provides L1 constructs for `AWS::BedrockAgentCore::*` resources and the L2 `Gateway` construct
- **`@aws-cdk/aws-bedrock-agentcore-alpha`** (experimental) — provides the L2 `Runtime`, `AgentRuntimeArtifact`, `WorkloadIdentity`, and related constructs we use to deploy the agents and MCP servers

Both packages are listed in `package.json`. The alpha designation on the second package means construct APIs may evolve; Workshop 2 pins specific versions and re-validates against newer versions in a documented upgrade cycle.

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

**How the persona reaches AgentCore Runtime.** The Wholesale UI and Wealth UI invoke AgentCore Runtime constructs via the `bedrock-agentcore:InvokeAgentRuntimeForUser` action, passing the Cognito JWT as the bearer token. The Runtime construct exchanges that token against AgentCore Identity, which validates the issuer (Cognito), extracts the persona claim, and makes it available to the agent's execution context. The agent reads the persona at the start of each invocation, validates it against its `VALID_PERSONAS` constant, and rejects mismatches before any tool call. This is the third validation point (Cognito issues, AgentCore Identity validates, agent verifies) — defense in depth for what is fundamentally a single trust claim.

**Why federate rather than manage users directly in Cognito?** Because the enterprise already has IDC. Duplicating user management in Cognito creates identity drift. Federation means a single source of truth for group membership, with Cognito as the application-facing token issuer.

### 4. AppSync GraphQL API

**What.** An AWS AppSync API whose schema is read from `spec/05-appsync-graphql/schema.graphql`. Resolvers federate across Neptune (direct SPARQL), Ontop (SPARQL-over-relational), and AWS Entity Resolution.

**Why AppSync and not a custom GraphQL server?** AppSync gives us Cognito integration (authorization by group claim), resolver-level caching, and subscription support for real-time signal updates — all without managing a server. The schema is FIBO-shaped, meaning the GraphQL types mirror FIBO classes. This is what makes Thesis 2 (two UIs, one backbone) work: both UIs query the same FIBO-shaped schema with different persona claims, and the resolvers return persona-scoped results.

### 5. Component deployments (12 AgentCore Runtimes + 5 step Lambdas + 1 Memory store)

**What.** The application logic for Workshop 2 deploys as three different resource types, each chosen for its fit:

| Resource type | Count | What it hosts |
|---|---|---|
| `agentcore.Runtime` | 12 | The 5 MCP servers and 7 standalone agents — all 12 MCP-shaped components from the Agent Registry |
| `aws_lambda.Function` | 5 | The Step Functions step Lambdas inside `referral-orchestrator` |
| `agentcore.CfnMemory` | 1 | The AgentCore Memory store backing `conversational-context-manager` |

**The 12 AgentCore Runtimes.** Each MCP component (5 servers + 7 agents) deploys as an `agentcore.Runtime` construct from `@aws-cdk/aws-bedrock-agentcore-alpha`. The artifact source is `AgentRuntimeArtifact.fromCodeAsset()`, which packages the component's source directory and uploads it to a CDK-managed S3 bucket at synth time. The entrypoint is `['opentelemetry-instrument', 'main.py']`, which wires AWS Distro for OpenTelemetry into every invocation automatically — execution traces appear in CloudWatch Transaction Search without per-handler instrumentation.

The 12 Runtime instances are:

| Component | Source directory | Discoverable by |
|---|---|---|
| `atlas-sparql-mcp` | `mcp-servers/atlas-sparql-mcp/` | All five personas |
| `atlas-shacl-mcp` | `mcp-servers/atlas-shacl-mcp/` | All five personas |
| `atlas-er-mcp` | `mcp-servers/atlas-er-mcp/` | All five personas |
| `atlas-fibo-mcp` | `mcp-servers/atlas-fibo-mcp/` | All five personas |
| `atlas-registry-mcp` | `mcp-servers/atlas-registry-mcp/` | All five personas |
| `nl-to-sparql-agent` | `agents/nl-to-sparql-agent/` | Banker, advisor, BSA, steward |
| `wealth-signal-detector` | `agents/wealth-signal-detector/` | Banker, advisor, steward |
| `household-traverser` | `agents/household-traverser/` | Banker, advisor |
| `referral-rationale-drafter` | `agents/referral-rationale-drafter/` | Banker |
| `behavioral-signal-agent` | `agents/behavioral-signal-agent/` | Advisor, steward |
| `theme-summarizer` | `agents/theme-summarizer/` | Advisor |
| `conversational-context-manager` | `agents/conversational-context-manager/` | Advisor |

Each Runtime ships with `loggingConfigs` sending APPLICATION_LOGS and USAGE_LOGS to CloudWatch Logs. APPLICATION_LOGS capture the agent's invocation-level events (request, response, errors); USAGE_LOGS capture session-level resource consumption (Memory reads, Bedrock token counts). Both feed CloudWatch Transaction Search for the audit story.

Step Functions step Lambdas are *not* Runtimes — see below.

**The 5 step Lambdas.** The `referral-orchestrator` workflow (construct 7) executes five steps via Step Functions: `select-advisor`, `validate-routing`, `write-routing-decision`, `notify-advisor`, `audit-write`. These deploy as standard `aws_lambda.Function` constructs with their own per-step IAM roles. They are **not** registered in Agent Registry and **not** exposed as MCP tools.

*Why these stay as Lambdas, not Runtimes.* Each step Lambda is a deterministic workflow component with one job: select an advisor by capacity, validate a routing decision against SHACL, write a triple to Neptune, send a notification, append an audit record. None of them needs MCP-shaped discovery, none takes a persona claim, none should be invokable from a UI. They exist only to be orchestrated by Step Functions. Lambda is the right primitive for this; the per-Lambda IAM role is the right scope; the absence from Agent Registry is correct.

*A teachable alternative.* If a team wanted maximum architectural uniformity — "everything is a Runtime" — they could deploy each step as its own `agentcore.Runtime` with a `Custom` registry record describing its internal-only nature. The cost: 5 extra Runtime instances, 5 extra ECR or S3 artifacts, 5 extra entries in Agent Registry that no UI ever queries, slower `cdk deploy` cycles. The benefit: every executable in the system is reachable via the same SDK, observable through the same Transaction Search view, governed through the same registry workflow. For Workshop 2's scale and teaching goals, the cost outweighs the benefit. For a production deployment with hundreds of agents and a mature platform team, the trade-off might flip. Knowing both patterns is part of becoming an AgentCore practitioner.

**The AgentCore Memory store.** A single `agentcore.CfnMemory` resource provisions one Memory store per deployed stack. The store is consumed only by `conversational-context-manager`; that Runtime's IAM execution role is granted `bedrock-agentcore:CreateEvent`, `bedrock-agentcore:GetEvent`, and `bedrock-agentcore:ListEvents` on the Memory ARN — no other Runtime has Memory access.

Within the Memory store, sessions are partitioned by the Cognito `sub` claim. When a Wealth Advisor opens the Themes route and asks a multi-turn question, the conversation lives in a session keyed to that advisor's `sub`. Another advisor logging in concurrently gets a different session in the same Memory store — no cross-user visibility. The Memory store itself is bounded to the deployed stack: every workshop attendee deploys their own stack in their own AWS account, so workshop attendees never share Memory either.

The Memory store has `removalPolicy: RemovalPolicy.DESTROY` so `cdk destroy` cleans up session data along with the rest of the stack. This is deliberate — workshop attendees shouldn't accumulate session data after they tear down their environment.

**How IAM policies are assigned.** The descriptor-as-source-of-truth pattern from the original spec carries forward. Each Runtime's IAM execution role policy is read directly from its JSON descriptor in `spec/04-aws-agent-registry/`. The CDK stack parses the `iam_policy.inline_policy` field and attaches it to the Runtime's role. No policy is hand-written in CDK code — the descriptors remain the single source of truth.

For step Lambdas, the IAM policy is sourced from the orchestrator's descriptor's `step_lambda_iam_policies` field (a new field that Phase 02 will add during the agent rewrite). Each step Lambda gets exactly the permissions its single job requires.

**How environment variables are assigned.** Same descriptor-as-source-of-truth pattern. Each component's environment variables are read from the `runtime.environment_variables` field in its JSON descriptor. Placeholder tokens like `${slgd_endpoint}` and `${neptune_cluster_arn}` are resolved to CDK token references at synth time.

**Why descriptor-driven assignment.** Governance, same as before. The JSON descriptors are reviewed by the platform team and committed alongside the component's MRM documentation. AgentCore Runtime constructs don't change this — they consume the descriptors the same way Lambda functions did. The deployment surface changes; the governance pattern stays.

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

**How `referral-orchestrator` registers in Agent Registry.** Unlike the 12 MCP-shaped components (which register via their `agentcore.Runtime` construct's automatic registration), the orchestrator is a CUSTOM record because its async-workflow invocation model doesn't fit the MCP synchronous request-response shape. The stack uses a CDK Custom Resource backed by a small registration Lambda to submit a CUSTOM record at deploy time. The record's `descriptors` block describes the workflow lifecycle: invocation pattern (`async_workflow`), execution ARN response shape, polling contract (`DescribeExecution` on the state machine ARN, terminal states `SUCCEEDED|FAILED|TIMED_OUT|ABORTED`), and final output schema. This is the one place the stack interacts with Agent Registry directly via the AWS SDK rather than through the AgentCore CDK constructs.

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
| Bedrock model access | Account-level setting | Not deployable via CDK; activated via the Bedrock console one-time |
| Bedrock inference profiles | AWS managed | The `us.anthropic.claude-sonnet-4-6` profile is referenced by ID; the profile itself exists in the account by default |
| AWS Agent Registry (the service itself) | AWS managed | The service exists per region; records are written into it by this stack at deploy time |
| Iceberg tables | Workshop 1 data pipeline | Data layer owned by data engineering |
| AgentCore Gateway | Not deployed | Workshop 2's MCP servers are MCP-native, so Gateway's protocol translation is unnecessary. Mentioned here for completeness — a production deployment wrapping non-MCP Lambdas would add this |

## Synthesis and deployment

**Prerequisites.** AWS CDK CLI v2.1102.0 or later (for AgentCore Runtime support including hotswap). The package.json includes:
- `aws-cdk-lib` (stable L1 constructs and the L2 `Gateway`)
- `@aws-cdk/aws-bedrock-agentcore-alpha` (the L2 `Runtime`, `WorkloadIdentity`, and related constructs)

**Synthesis and deployment commands:**

```bash
cd use-case-applications/cdk
npm install
npx cdk synth --context neptuneClusterEndpoint=<endpoint> \
              --context neptuneClusterArn=<arn> \
              --context vpcId=<vpc-id> \
              --context privateSubnetIds=<subnet-1,subnet-2>
npx cdk deploy
```

**Deployment ordering.** The deploy completes in two phases automatically:

1. **CloudFormation phase.** All AWS resources provision: the 12 Runtime instances (with their automatic Runtime → registry record syncing), the 5 step Lambdas, the Memory store, Cognito, AppSync, etc.

2. **Custom Resource phase.** The `referral-orchestrator` CUSTOM record gets registered in Agent Registry by the CDK Custom Resource. This runs after the Step Functions state machine ARN is known (the ARN goes into the record's `descriptors`).

After `cdk deploy` completes, the Wholesale UI and Wealth UI can immediately query Agent Registry and discover all 13 components (12 auto-registered MCP records + 1 CUSTOM record). No manual registration step is required.

**Why a single CloudFormation stack and not multiple.** The original rationale holds: all constructs share the VPC, the Cognito pool, and cross-references between Runtime ARNs. Splitting into multiple stacks would require export/import for every cross-reference — added complexity with no isolation benefit at workshop scale.

**Hotswap for development.** AgentCore Runtime supports CDK's hotswap deployment for ECR and S3 artifact updates. During Phase 2 of the workshop, when attendees iterate on agent code, `cdk deploy --hotswap` updates the Runtime's artifact without going through CloudFormation — typical iteration time drops from 8-12 minutes to 30-60 seconds. **Do not use `--hotswap` for production deployments**; it introduces CloudFormation drift and is intended only for development cycles.

## Teaching note

The CDK stack is deployed once at the start of Phase 1, before the first notebook runs. The notebooks do not deploy infrastructure — they consume it. This separation is deliberate: the novice should understand that infrastructure and application logic are different concerns with different change cadences, different review processes, and different blast radii. A notebook that deploys a Lambda on every run is teaching the wrong lesson about production operations.
