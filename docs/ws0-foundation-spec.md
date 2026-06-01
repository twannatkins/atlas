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
