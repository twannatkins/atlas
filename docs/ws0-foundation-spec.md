# WS0 Foundation template spec

**Status:** Draft — Pass 2 of 3. No foundation template has been built yet. This doc is the spec for it.

---

## Key finding: WS1 does NOT create a VPC

`agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` takes `VpcId` and `SubnetIds` as
CloudFormation **parameters**. Relevant extract:

```yaml
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC where Neptune clusters will be deployed
  SubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: At least two subnets in different AZs within the VPC
```

The template creates: `NeptuneSecurityGroup`, `NeptuneSubnetGroup`, `NeptuneS3Role`, two Neptune
clusters (`LGDCluster` / `SLGDCluster`), two instances, `OntologyStagingBucket`, and
`NeptuneIamAuthPolicy`. It does not create or reference `AWS::EC2::VPC`, `AWS::EC2::Subnet`,
`AWS::EC2::InternetGateway`, or `AWS::EC2::NatGateway`.

The WS2 preflight notebook (`notebooks/phase-1-referral/00_preflight.ipynb`, cell 16) confirms the
assumed pre-existing VPC is the **SageMaker Unified Studio domain VPC** ("The Workshop 1 VPC is the
SageMaker Unified Studio domain VPC and should have at least four private subnets."). The bridge
derives VpcId and private subnet IDs from the Neptune security group ID (a WS1 CFN output) via EC2
`describe_security_groups` + `describe_subnets` with a "Private" name-tag heuristic or
`MapPublicIpOnLaunch=False` fallback.

**Consequence:** in the author's account this works because SageMaker Studio already provisions a
labelled VPC. In other runner accounts that VPC does not exist, and the heuristic breaks. A Foundation
template provisions the shared baseline once so all runners start from identical state.

---

## What the Foundation template must provision

The Foundation template (stack name: `atlas-foundation`, or `ws0-foundation` following the author's
naming) establishes the networking baseline WS1 and WS2 both assume.

### Required resources

| Resource | Notes |
|---|---|
| `AWS::EC2::VPC` | CIDR `10.0.0.0/16`. Enable DNS hostnames + resolution. |
| `AWS::EC2::Subnet` × 2 (public) | One per AZ, CIDR `/24` (e.g. `10.0.0.0/24`, `10.0.1.0/24`). `MapPublicIpOnLaunch: true`. |
| `AWS::EC2::Subnet` × 2 (private) | One per AZ, CIDR `/24` (e.g. `10.0.2.0/24`, `10.0.3.0/24`). `MapPublicIpOnLaunch: false`. |
| `AWS::EC2::InternetGateway` + attachment | Attached to the VPC. Public subnets route `0.0.0.0/0` through it. |
| `AWS::EC2::NatGateway` × 1 | In one public subnet (single-AZ NAT is sufficient for a workshop; note this in template comments). EIP required. |
| Route tables | Public RT (IGW route), private RT (NAT route). Associate each subnet. |
| `AWS::EC2::SecurityGroup` (base) | Optional: a "workshop baseline" SG that allows HTTPS egress (443) and Neptune (8182) within the VPC. WS1 and WS2 add their own SGs on top; this is just a convenient common ancestor. |

### What to export

The template must export these values as CloudFormation outputs with logical export names so WS1 and
WS2 can import them via `Fn::ImportValue`:

| Export name | Value | Consumed by |
|---|---|---|
| `atlas-foundation-vpc-id` | `!Ref VPC` | WS1 (parameter), WS2 CDK context |
| `atlas-foundation-private-subnet-ids` | Comma-joined private subnet IDs | WS1 (parameter), WS2 CDK context |
| `atlas-foundation-public-subnet-ids` | Comma-joined public subnet IDs | WS2 CDK (ALB, CloudFront origin) |
| `atlas-foundation-vpc-cidr` | `10.0.0.0/16` | WS1 NeptuneSecurityGroup CidrIp |

No SageMaker Studio domain export is required for WS1/WS2 to function (see Open Questions).

### What WS1 currently exports (for reference)

WS1 already exports `atlas-lgd-endpoint`, `atlas-slgd-endpoint`, `atlas-neptune-sg`,
`atlas-ontology-bucket`, `atlas-neptune-s3-role-arn`, `atlas-neptune-iam-auth-policy`. It does not
export `VpcId` or subnet IDs — those are WS0's responsibility.

---

## How WS1 and WS2 change to consume it

### WS1 change (future pass, not this pass)

`atlas-neptune-twotier.yaml` parameters `VpcId` and `SubnetIds` would gain a default that reads from
Foundation exports, or the runner passes `atlas-foundation-vpc-id` and
`atlas-foundation-private-subnet-ids` directly as parameter values:

```bash
aws cloudformation deploy \
  --template-file atlas-neptune-twotier.yaml \
  --parameter-overrides \
    VpcId=$(aws cloudformation list-exports --query "Exports[?Name=='atlas-foundation-vpc-id'].Value" --output text) \
    SubnetIds=$(aws cloudformation list-exports --query "Exports[?Name=='atlas-foundation-private-subnet-ids'].Value" --output text) \
    ...
```

Alternatively, WS1 can import directly using `Fn::ImportValue: atlas-foundation-vpc-id` for resources
that accept it, and a `AWS::SSM::Parameter` intermediate for resources that require a literal string
(Neptune subnet group).

### WS2 bridge change (eliminates the heuristic)

The WS2 preflight bridge cell (cell 16 in `00_preflight.ipynb`) currently derives VpcId and private
subnets from the Neptune SG via EC2 API heuristics. Once the Foundation template exists and exports
`atlas-foundation-vpc-id` and `atlas-foundation-private-subnet-ids`, the bridge reads those exports
directly:

```python
# Replaces the EC2 describe_security_groups + describe_subnets heuristic
cfn = boto3.client("cloudformation", region_name=AWS_REGION)
exports = {e["Name"]: e["Value"] for e in cfn.list_exports()["Exports"]}
vpc_id = exports["atlas-foundation-vpc-id"]
private_subnet_ids_str = exports["atlas-foundation-private-subnet-ids"]
```

This is deterministic across all runner accounts.

---

## Workshop Studio fit

The Foundation template is what AWS Workshop Studio's "Account provisioning" step deploys. In the
Workshop Studio model, the event operator deploys one or more setup CloudFormation templates before
runners receive their accounts. The Foundation template is that setup template for ATLAS: it creates
the VPC baseline so runners open an account that already has `atlas-foundation-*` CFN exports
available. WS1 and WS2 then read those exports rather than discovering or creating networking
themselves.

The deployment order is:

1. **WS0 Foundation** (`atlas-foundation` stack) — networking baseline; exports VpcId, subnets
2. **WS1** (`atlas-neptune-twotier` stack) — Neptune clusters + S3 bucket; reads VpcId/subnets from WS0 exports
3. **WS2** (`AtlasWorkshop2Stack`) — agents, MCP servers, UIs; reads all WS1 + WS0 exports via bridge

---

## Token resolution and descriptor governance

`spec/04-aws-agent-registry/` descriptors use `${ontology_staging_bucket}`, `${atlas_sparql_mcp_arn}`,
etc. as placeholder tokens. These are **governed documentation tokens**, not runtime template
variables.

CDK resolves actual values from context (`tryGetContext("ontologyStagingBucket")` → `props`) and
CDK token references (`this.atlasSparqlMcp.agentRuntimeArn`). The `register.py` scripts do not
pass `runtime.environment_variables` or `iam_policy` to `register_agent` — they register only the
schema/metadata payload. So `${ontology_staging_bucket}` in descriptor `iam_policy.Resource` fields
is reference documentation for what the CDK construct should produce, not a string the registry
ingests.

**Gap for follow-on (not this pass):** `register.py` does not resolve `${ontology_staging_bucket}`
tokens at registration time. Both `nl-to-sparql-agent/register.py` and
`wealth-signal-detector/register.py` call `client.register_agent(agentName, description, version,
inputSchema, outputSchema, registryMetadata)` — they do not pass `runtime.environment_variables` or
`iam_policy` to the registry API, so the token is never substituted. The descriptor's bucket
references serve as governed documentation (what the CDK construct *should* deploy) rather than
executable registry payloads. A future pass could add a registration-time substitution step that
reads the deployed stack's `ontologyStagingBucket` output and interpolates tokens before registering
IAM posture metadata, if the registry API eventually accepts that payload.

---

## Open questions (require owner input)

1. **Does ATLAS require a SageMaker Studio domain at all?** The Phase 1 use case (AgentCore runtimes,
   Lambda, ECS Fargate, Neptune, Bedrock) does not inherently require SageMaker Studio. Studio was the
   historical authoring environment. If the workshop no longer requires Studio for notebook execution
   (e.g. runners use JupyterHub or Cloud9 instead), the Foundation template does not need to provision
   a Studio domain, and the VPC's provenance shifts entirely to WS0. Clarify before building the
   Foundation template to avoid provisioning a Studio domain that the workshop no longer uses.

2. **Single-AZ NAT vs multi-AZ:** A single NAT gateway is cheaper for a workshop but creates an AZ
   dependency for Lambda/ECS egress. Decision: single-AZ is acceptable for a time-limited workshop
   event; note it explicitly in the template description.

3. **Existing account VPC conflicts:** Some AWS event accounts arrive with a default VPC that may
   conflict on CIDR or name. The Foundation template should use a non-default CIDR (`10.0.0.0/16`)
   and tag all resources `Project: atlas` to distinguish them from the default VPC.

4. **SageMaker execution role:** The `NeptuneIamAuthPolicy` in WS1 is described as attaching to
   "SageMaker execution roles, Lambda execution roles, and ECS task roles." If WS0 provisions a
   SageMaker execution role (required if Studio is kept), WS0 should also export its ARN so WS1 can
   attach the policy without hardcoding a role name.

---

## Account-level prerequisites — full inventory (confirmed during WS2 capstone deploy)

The networking baseline (VPC/subnets/NAT) described above is necessary but not sufficient. Live WS1 and
WS2 deployment revealed a broader set of account-level prerequisites that must be established before
either workshop deploys cleanly in a fresh account. This section expands the WS0 Foundation scope to
cover the complete picture.

The items below are organized by how they must be delivered: automatable via CFN/CDK (the Foundation
template does it) versus manual operator steps (console actions that cannot be expressed in CloudFormation).
This distinction is the central design question for the WS0 package.

---

### Group A — Automatable by the Foundation template (CFN/CDK)

#### A1. SageMaker Unified Studio domain, user profile, and execution roles

WS1 and WS2 notebooks run inside SageMaker Studio. The domain, user profile, and the execution
role(s) that notebooks run as must all pre-exist before WS1 begins.

**Why this is harder than it looks.** SageMaker Unified Studio (DataZone-backed) creates **two**
DataZone-managed execution roles per domain: the *domain default role* and a separate *kernel-running
role* that is actually used when a notebook cell executes. Both roles must receive all IAM permissions
that WS1 notebooks require. Applying permissions only to the domain default role (the intuitive choice)
does nothing because the notebook actually runs as the kernel role — a behavior that is not visible in
the console and is not documented in the Studio setup guide.

The Foundation template should either provision the Studio domain and export both role ARNs, or export
a single consolidated execution role ARN that WS0 creates and provisions explicitly. Whichever path is
chosen, the role ARN(s) must be available as CFN exports so WS1 and the Foundation runbook can attach
policies to the correct targets without hardcoding names.

**Open question (carried from earlier):** does ATLAS still require SageMaker Studio for notebook
execution, or can runners use a lighter-weight environment (JupyterHub, local)? If Studio is no longer
required, this entire item drops from WS0. Do not provision a Studio domain until this is resolved —
Studio domains are expensive to provision and difficult to delete cleanly.

**Consequence if missing:** WS1 Module 3 notebook cells cannot run. The CFN deploy cell will fail
at the `sts:AssumeRole` boundary. The kernel will not be able to call Neptune, S3, or CloudFormation.

#### A2. IAM policy attachment and supplemental permissions on the execution role(s)

WS1's CFN template creates the `atlas-neptune-iam-auth` managed policy but **never attaches it to any
role**. This is a `LIVE-STATE SELF-BITING` gap: the policy exists after WS1 deploys, but the notebook
execution roles do not have it, so Neptune IAM auth fails silently (requests 403 with no useful error
message).

The Foundation template (or its post-deploy runbook step) must:

1. Attach `atlas-neptune-iam-auth` to both execution roles after WS1's CFN stack is deployed. (This
   requires WS1 to have been deployed first, so this is technically a post-WS1 step, but it belongs
   in the WS0 runbook as a cross-stack wiring step.)
2. Add an inline policy granting the execution roles:
   - `cloudformation:DescribeStacks` on the WS1 stack ARN (WS1 notebooks read their own CFN outputs)
   - `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on the ontology staging bucket (bulk load and
     artifact reads)
   - `rds:DescribeDBClusters` on both Neptune cluster ARNs (Gate 4 in WS1 Module 3)
3. Add `bedrock:InvokeModel` on Bedrock ARNs to both execution roles for WS1 Modules 7–8 and all
   WS2 notebook cells that call Titan Embeddings or Claude Sonnet.

**The two-role problem is the most dangerous gap here.** Any time a new permission is added to "the
execution role," both DataZone-managed roles must receive it. A future Foundation pass should provision
a single explicit IAM role with all required permissions and configure the Studio domain to use it,
eliminating the two-role confusion entirely.

**Consequence if missing:** WS1 Gate 4 fails (`rds:DescribeDBClusters`). Neptune writes silently 403.
WS1 Modules 7–8 fail with `AccessDeniedException` on Bedrock. WS2 notebooks fail the same way.

#### A3. IDC persona groups for WS2

WS2's four-layer permission model starts at IAM Identity Center. Five groups must exist:

| Group name | Persona | Consequence if missing |
|---|---|---|
| `atlas-consumer-banker` | Wholesale UI user | Cognito federation returns no group claim; user gets default (no-access) policy |
| `atlas-wealth-advisor` | Wealth UI user | Same |
| `atlas-bsa-analyst` | BSA routes in both UIs | Same |
| `atlas-ontology-steward` | Admin routes | Same |
| `atlas-auditor` | Read-only audit access | Same |

WS2's CDK stack provisions a Cognito User Pool federated from IDC. If the IDC groups do not exist at
the time the Cognito federation resolves, the permission model collapses: all authenticated users
receive the same default policy (no persona scoping), and persona-gated features silently return empty
results rather than failing loudly.

**Automatable IF IDC is enabled in the account.** IAM Identity Center group creation is automatable
via the `aws sso-admin` and `aws identitystore` CLI/SDK. The Foundation template can provision them
using a CFN Custom Resource backed by a Lambda. The dependency is that IAM Identity Center must already
be enabled in the account — a new AWS account has IDC available but not enabled; enabling it is a
one-time console action (Group B below).

**Consequence if missing:** WS2 demo runs but persona gating is non-functional. Consumer Banker sees
all customers. BSA routes are visible to everyone. The regulatory teaching story breaks.

#### A4. Lake Formation admin grant

WS2's `LakeFormationConstruct` creates Lake Formation tag policies for persona-scoped data access.
This requires `lakeformation:CreateLFTag` on the catalog, which is only available to LF
data-lake administrators.

In a fresh AWS account the only default LF admin is the root user. The CDK CloudFormation execution
role does not have LF admin by default, so `LakeFormation::Tag` resource creation fails with
`AccessDenied`.

**Required setup step (one-time, per account):**

```bash
aws lakeformation put-data-lake-settings \
  --data-lake-settings '{
    "DataLakeAdmins": [
      {"DataLakePrincipalIdentifier":
        "arn:aws:iam::<account>:role/cdk-hnb659fds-cfn-exec-role-<account>-<region>"}
    ]
  }' \
  --region <region>
```

This can be delivered as a CFN Custom Resource in the Foundation template (a Lambda that calls
`put-data-lake-settings`) or as a manual step in the runbook. Either path is acceptable; the
Foundation template approach is preferred for reproducibility.

**Current WS2 status:** `LakeFormationConstruct` is commented out in `atlas-workshop-2-stack.ts`.
LF tagging is not exercised in Phase 1. Re-enable once the LF admin grant is wired into WS0.

**Consequence if missing:** WS2 deploy fails with `AccessDenied` on `LakeFormation::Tag` when the
construct is re-enabled. Data-layer persona scoping (Layer 3 of the four-layer model) is non-functional.

#### A5. CDK bootstrap

WS2 deploys via CDK. CDK requires a one-time bootstrap of the target account and region — this creates
the `CDKToolkit` stack, the CDK assets S3 bucket, and the CDK execution role. Without it, `cdk deploy`
fails immediately.

```bash
cdk bootstrap aws://<account-id>/us-east-1
```

This is idempotent and safe to re-run. It should be the first step in the WS0 runbook, before any
CFN stack is deployed.

**Consequence if missing:** `cdk deploy` fails with "This stack uses assets, so the toolkit stack must
be deployed to the environment."

---

### Group B — Manual operator steps (console or CLI; not CFN-automatable)

These items cannot be expressed in CloudFormation because they operate at a layer above or outside the
CFN resource model.

#### B1. Bedrock model access enablement

WS1 Modules 7–8 and three WS2 agents (`nl-to-sparql-agent`, `referral-rationale-drafter`,
`theme-summarizer`) call Bedrock foundation models. Two models must be enabled:

- `amazon.titan-embed-text-v2:0` — Titan Embeddings v2, used for semantic SPARQL retrieval
- `us.anthropic.claude-sonnet-4-6` — US cross-region inference profile for Claude Sonnet

**Why this cannot be automated.** Bedrock model access is an account-level entitlement, not an IAM
permission. Granting `bedrock:InvokeModel` in IAM is necessary but not sufficient — the model must
also be independently enabled via the Bedrock console "Model access" page. There is no CloudFormation
resource type or API that automates this step; it requires a human to click "Enable" in the console.

**Non-US region note.** The `us.anthropic.claude-sonnet-4-6` profile is the US cross-region pool.
For accounts running in non-US regions, the profile ID is `global.anthropic.claude-sonnet-4-6`. This
is currently hardcoded in all 12 WS2 runtime environment variables and in WS1 notebooks. The portability
refactor (tracked separately) must address this before the workshop can run outside `us-east-1`.

**Consequence if missing:** WS1 Modules 7–8 fail with `AccessDeniedException`. WS2 agents that call
Bedrock silently return empty responses or hard errors depending on which code path is hit.

#### B2. IAM Identity Center enablement

IDC persona groups (A3 above) require IAM Identity Center to be enabled in the account. Enabling IDC
is a one-time console action — it cannot be done via CloudFormation. A fresh AWS account has IDC
available but not active.

**Operator step:** open the IAM Identity Center console and click "Enable." This takes about 60 seconds
and is irreversible for the account. Once IDC is enabled, the Foundation template's Custom Resource (A3)
can create the persona groups programmatically.

**Consequence if missing:** IDC group creation fails. Cognito federation configuration fails. WS2 CDK
deploy may succeed but persona gating is broken.

---

### Group C — Operator toolchain prerequisites (not account-level, but must be documented)

These are requirements on the machine that runs `cdk deploy`, not on the AWS account itself. They are
not provisioned by the Foundation template, but they must be documented in the WS0 runbook.

#### C1. Docker running at synth time

WS2's `OrchestratorRegistration` Lambda bundles `boto3>=1.43` via Docker at `cdk synth` time
(`Code.fromAsset` with `BundlingOptions`). If Docker is not running on the machine executing `cdk
synth`, the synth fails immediately with a Docker daemon connection error.

**Why this matters for portability.** A runner following a workshop guide in a browser-based Cloud9
environment or a SageMaker terminal may not have Docker available. Options for a future pass:
- Pre-build the Lambda ZIP and store it in S3 or commit it as a checked-in asset (eliminates the
  Docker requirement entirely)
- Replace `Code.fromAsset` with a Lambda layer that pins boto3 (no bundling needed)
- Use a pre-built ECR image for the provider Lambda

This is not solved in the current code. It is a known portability hazard: the workshop works if Docker
is running locally, fails silently if it is not.

#### C2. Region hardcoding — `us-east-1` and `us.` inference profile

The following are currently hardcoded and will fail for non-US runners:

- All 12 AgentCore runtime environment variables set `BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6"`
- WS1 notebooks default all `boto3.client()` calls to `us-east-1`
- WS2 `cdk.json` and CDK context assume `us-east-1`
- The `us.anthropic.claude-sonnet-4-6` inference profile is US-only

The full portability refactor (adding a `REGION` constant, switching to `global.*` inference profile,
parameterizing the CDK stack) is tracked as P1 in the portability findings and is deferred until both
workshops are verified end-to-end in this account. It must be completed before the workshop can be
offered in non-US regions.

---

### Group D — Known placeholders (not account-prep, but tracked here for completeness)

#### D1. Ontop mapping files

WS2's Ontop ECS service is deployed with `desiredCount: 0` because the R2RML mapping files
(`atlas.obda`, `atlas.properties`) have not been authored. The Ontop container exits immediately
on startup without these files, so the ECS service never reaches a healthy state and CloudFormation
times out.

This is a content gap, not an account-prep gap. The WS0 Foundation package does not need to address
it. It is tracked here so it is not mistaken for a missing account prerequisite when the Ontop pass
runs: the account is correctly configured; the content simply needs to be written.

---

### Summary: what WS0 must own

| Item | Delivery | Timing |
|---|---|---|
| VPC, subnets, NAT, routing (see §"What the Foundation template must provision") | Foundation CFN template | Before WS1 |
| CDK bootstrap (A5) | One-time CLI command in runbook | Before WS2 |
| SageMaker Studio domain + execution roles, if Studio is still required (A1) | Foundation CFN template or runbook | Before WS1 |
| IAM policy attachment + supplemental permissions on execution roles (A2) | Post-WS1 runbook step | After WS1 CFN deploy |
| IDC persona groups (A3) | Foundation CFN Custom Resource (requires IDC enabled first) | Before WS2 |
| Lake Formation admin grant (A4) | Foundation CFN Custom Resource or runbook step | Before WS2 |
| Bedrock model access enablement — Titan + Claude Sonnet (B1) | Manual console step; document in runbook | Before WS1 Module 7 |
| IAM Identity Center enablement (B2) | Manual console step; document in runbook | Before IDC group creation |
| Docker on synth machine (C1) | Documented in runbook; not resolved in code yet | Before WS2 cdk deploy |
| Region hardcoding / non-US portability (C2) | Deferred — portability refactor pass | Before non-US publication |
| Ontop mapping files (D1) | Content work — separate pass | Before Ontop pass |
