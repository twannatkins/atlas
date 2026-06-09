---
title: "Cleanup"
weight: 999
---

# Cleanup — Tear Down Workshop 2 Infrastructure

## Why Cleanup Matters

Workshop 2 deploys resources that cost money when left running. The most significant charges are:

| Resource | Approximate daily cost | Notes |
|---|---|---|
| Neptune serverless (2 clusters) | ~$17/day | Inherited from Workshop 1 |
| ECS Fargate (Ontop) | ~$2/day | Does not scale to zero by default |
| AgentCore Runtimes (12) | ~$3/day | Per-invocation minimum |
| AppSync | ~$1/day | Low when idle |
| CloudFront | < $1/day | Low when idle |

**Total for a workshop left running after completion: ~$24/day**

If you are done with Workshop 2, tear down the `AtlasWorkshop2` stack and the Workshop 1 Neptune clusters. The ontology, agents, notebooks, and CDK code remain in your repository — you can redeploy the full environment at any time.

---

## Step 1 — Destroy the Workshop 2 CDK stack

Workshop 2 is a **single CDK stack — `AtlasWorkshop2`**. The CDK app synthesizes one
stack that contains everything Workshop 2 deploys: the AppSync GraphQL API and its
resolvers (including the in-VPC SPARQL resolver and the `takeOnClient` /
`resetDemoRoutings` mutations), the Cognito user pool, the AgentCore runtimes and the
AgentCore Memory store, Ontop on ECS Fargate, both UIs' S3 buckets + CloudFront
distributions, and the Step Functions referral orchestrator. Tearing it down is therefore
one `cdk destroy`. (Workshop 1's Neptune clusters are a *separate* stack,
`atlas-neptune-twotier` — see Step 4.)

From your terminal or SageMaker notebook terminal:

```bash
cd ~/atlas/use-case-applications/cdk
cdk destroy --all
```

`--all` resolves to the single `AtlasWorkshop2` stack (equivalently:
`cdk destroy AtlasWorkshop2`). CDK prompts you to confirm; type `y`.

Expected output (after the stack is destroyed):

```
✅  AtlasWorkshop2: destroyed
```

Destroying `AtlasWorkshop2` removes the Cognito user pool, the AppSync API, the
CloudFront distributions, the ECS/Ontop service, and the AgentCore runtimes + Memory
store with it — they are all resources *within* that one stack, not separate stacks.

---

## Step 2 — Remove Agent Registry records

The Agent Registry records are not managed by CDK and must be deleted manually:

```bash
# List all atlas registry records
aws bedrock-agentcore-control list-registry-records \
    --region us-east-1 \
    --query 'registryRecords[?starts_with(name, `atlas`)].[recordId, name]' \
    --output table

# Delete each record (repeat for each record ID shown)
aws bedrock-agentcore-control delete-registry-record \
    --record-id <record-id> \
    --region us-east-1
```

Or delete all Workshop 2 records with a loop:

```bash
aws bedrock-agentcore-control list-registry-records \
    --region us-east-1 \
    --query 'registryRecords[?starts_with(name, `atlas`)].recordId' \
    --output text | tr '\t' '\n' | while read id; do
  echo "Deleting $id"
  aws bedrock-agentcore-control delete-registry-record \
      --record-id "$id" --region us-east-1
done
```

---

## Step 3 — (Usually not needed) the AgentCore Memory store

The AgentCore Memory store is a resource **inside the `AtlasWorkshop2` stack** (logical
type `AWS::BedrockAgentCore::Memory`, physical id `atlas_workshop_memory-…`), so `cdk
destroy` in Step 1 removes it — you do **not** normally delete it by hand. If you ever need
to delete it directly, resolve the real id from the stack first (it is CDK-generated, not a
fixed name):

```bash
MEMORY_ID=$(aws cloudformation describe-stack-resources \
    --stack-name AtlasWorkshop2 --region us-east-1 \
    --query "StackResources[?ResourceType=='AWS::BedrockAgentCore::Memory'].PhysicalResourceId | [0]" \
    --output text)
echo "Memory: $MEMORY_ID"   # e.g. arn:aws:bedrock-agentcore:...:memory/atlas_workshop_memory-XXXX
# aws bedrock-agentcore-control delete-memory --memory-id "$MEMORY_ID" --region us-east-1
```

---

## Step 4 — Tear down Workshop 1 Neptune clusters

If you are also done with Workshop 1:

### Option A: AWS Console

1. Open the [CloudFormation console](https://console.aws.amazon.com/cloudformation/) in us-east-1
2. Select the stack named `atlas-neptune-twotier`
3. Choose **Delete** and confirm

### Option B: AWS CLI

```bash
aws cloudformation delete-stack \
    --stack-name atlas-neptune-twotier \
    --region us-east-1

aws cloudformation wait stack-delete-complete \
    --stack-name atlas-neptune-twotier \
    --region us-east-1
```

---

## Step 5 — Remove Cognito users and user pool (optional)

If you do not need the workshop Cognito users:

```bash
# Get the user pool ID from the CDK output (or the console)
USER_POOL_ID="us-east-1_XXXXXXXXX"

# Delete the workshop users (the pool uses email as the username)
aws cognito-idp admin-delete-user \
    --user-pool-id $USER_POOL_ID \
    --username dana.brooks@atlas.demo \
    --region us-east-1

aws cognito-idp admin-delete-user \
    --user-pool-id $USER_POOL_ID \
    --username marcus.webb@atlas.demo \
    --region us-east-1
```

The Cognito user pool itself is part of the Workshop 2 app stack (`AtlasWorkshop2`), so it is deleted when you tear that stack down in Step 1 (`cdk destroy --all`). Deleting the users above is only needed if you want to remove them while keeping the pool.

---

## Step 6 — Verify no resources remain

```bash
# The single most reliable check: the app stack should be gone after Step 1.
aws cloudformation describe-stacks --stack-name AtlasWorkshop2 --region us-east-1 \
    2>/dev/null && echo "STILL PRESENT — re-run Step 1" || echo "AtlasWorkshop2: gone"

# Check for remaining AgentCore Runtimes
aws bedrock-agentcore-control list-agent-runtimes \
    --region us-east-1 \
    --query 'agentRuntimes[?starts_with(name, `atlas`)]'

# Check for remaining Registry records
aws bedrock-agentcore-control list-registry-records \
    --region us-east-1 \
    --query 'registryRecords[?starts_with(name, `atlas`)]'

# Check for Neptune clusters (Workshop 1 — only gone if you also ran Step 4)
aws neptune describe-db-clusters \
    --region us-east-1 \
    --query "DBClusters[?contains(DBClusterIdentifier, 'atlas')]"
```

The ECS/Ontop cluster has a CDK-generated name (`AtlasWorkshop2-OntopCluster…`), not a
fixed `atlas-ontop` — but you do not need to check it by name: it is a resource inside
`AtlasWorkshop2`, so if the stack is gone (first command), the cluster is gone with it.
Each command should return empty results, "gone", or a "not found" error.

---

## Cost Summary

If you completed both phases in two working days and cleaned up immediately afterward:

| Item | Cost |
|---|---|
| Workshop 1 (Day 1) | ~$10–$18 |
| Workshop 2 (Day 2) | ~$25–$40 |
| **Total** | **$35–$58** |

---

## What You Built

Over the course of Workshop 2, you built and deployed:

Everything below is provisioned by the **single `AtlasWorkshop2` CDK stack** (the "Where"
column names the construct within that stack, not separate stacks):

| Layer | What | Where (construct in `AtlasWorkshop2`) |
|---|---|---|
| Capability surface | 5 MCP server AgentCore Runtimes | agent-runtime constructs |
| Phase 1 agents | 5 AgentCore Runtimes | agent-runtime constructs |
| Phase 2 agents | 3 AgentCore Runtimes (incl. memory-backed) | agent-runtime constructs |
| Federation | Ontop on ECS Fargate (3 R2RML mappings) | ECS cluster/service/task + ALB |
| API | FIBO-shaped AppSync GraphQL | AppSync API + resolvers (incl. in-VPC SPARQL resolver, `takeOnClient`/`resetDemoRoutings`) |
| Auth | Cognito user pool + groups + hosted UI | Cognito construct |
| Memory | AgentCore Memory store (`atlas-wealth-conv`) | `AWS::BedrockAgentCore::Memory` |
| Wholesale UI | React app on CloudFront | S3 bucket + CloudFront distribution |
| Wealth UI | React app on CloudFront | S3 bucket + CloudFront distribution |
| Registry | Agent Registry records | custom resource (auto-register) |

The code, notebooks, spec, and ontology remain in your repository. The stack is
reproducible from source. The workshop can be re-deployed at any time by running
`cdk deploy --all` from `use-case-applications/cdk/` (which deploys the one
`AtlasWorkshop2` stack). The separate `atlas-neptune-twotier` stack from Workshop 1 owns
the Neptune clusters the app reads.

---

## Thank You

You have completed the ATLAS workshop — both phases.

The semantic layer is built. The agents are governed. The boundary between deterministic and probabilistic is enforced in code. The audit trail is queryable end-to-end. The two UIs serve the right data to the right personas. The Rachel Kim referral flows cleanly from signal to advisor without a hallucination anywhere in the path.

That is what governed agentic AI in a regulated industry looks like when it is built correctly.
