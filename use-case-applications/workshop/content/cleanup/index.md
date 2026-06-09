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

If you are done with Workshop 2, tear down all CDK stacks and the Neptune clusters. The ontology, agents, notebooks, and CDK code remain in your repository — you can redeploy the full environment at any time.

---

## Step 1 — Destroy the Workshop 2 CDK stacks

From your terminal or SageMaker notebook terminal:

```bash
cd ~/atlas/use-case-applications/cdk
cdk destroy --all
```

CDK will prompt you to confirm deletion of each stack. Type `y` for each.

Expected output (after all stacks are destroyed):

```
✅  atlas-phase2-agents-stack: destroyed
✅  atlas-memory-stack: destroyed
✅  atlas-wealth-ui-stack: destroyed
✅  atlas-wholesale-ui-stack: destroyed
✅  atlas-auth-stack: destroyed
✅  atlas-appsync-stack: destroyed
✅  atlas-ontop-stack: destroyed
✅  atlas-mcp-stack: destroyed
```

### Option B: destroy individual stacks

If you want to keep some stacks running while tearing down others, destroy them individually:

```bash
# Destroy in reverse dependency order
cdk destroy atlas-wealth-ui-stack
cdk destroy atlas-wholesale-ui-stack
cdk destroy atlas-phase2-agents-stack
cdk destroy atlas-memory-stack
cdk destroy atlas-auth-stack
cdk destroy atlas-appsync-stack
cdk destroy atlas-ontop-stack
cdk destroy atlas-mcp-stack
```

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

## Step 3 — Delete the AgentCore Memory store

```bash
aws bedrock-agentcore-control delete-memory \
    --memory-namespace atlas-wealth-conv \
    --region us-east-1
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
# Check for remaining AgentCore Runtimes
aws bedrock-agentcore-control list-agent-runtimes \
    --region us-east-1 \
    --query 'agentRuntimes[?starts_with(name, `atlas`)]'

# Check for remaining Registry records
aws bedrock-agentcore-control list-registry-records \
    --region us-east-1 \
    --query 'registryRecords[?starts_with(name, `atlas`)]'

# Check for Neptune clusters
aws neptune describe-db-clusters \
    --region us-east-1 \
    --query "DBClusters[?contains(DBClusterIdentifier, 'atlas')]"

# Check for ECS services (Ontop)
aws ecs list-services \
    --cluster atlas-ontop \
    --region us-east-1 2>/dev/null || echo "ECS cluster already deleted"
```

All four commands should return empty results or "not found" errors.

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

| Layer | What | Where |
|---|---|---|
| Capability surface | 5 MCP server AgentCore Runtimes | CDK `atlas-mcp-stack` |
| Phase 1 agents | 5 AgentCore Runtimes | CDK `atlas-mcp-stack` / agents stack |
| Phase 2 agents | 3 AgentCore Runtimes (incl. memory-backed) | CDK `atlas-phase2-agents-stack` |
| Federation | Ontop on ECS (3 R2RML mappings) | CDK `atlas-ontop-stack` |
| API | FIBO-shaped AppSync GraphQL | CDK `atlas-appsync-stack` |
| Auth | Cognito + IDC federation + Lake Formation | CDK `atlas-auth-stack` |
| Memory | AgentCore Memory store (`atlas-wealth-conv`) | CDK `atlas-memory-stack` |
| Wholesale UI | React app on CloudFront | CDK `atlas-wholesale-ui-stack` |
| Wealth UI | React app on CloudFront | CDK `atlas-wealth-ui-stack` |
| Registry | 13 AWS Agent Registry records | Manual + CDK auto-register |

The code, notebooks, spec, and ontology remain in your repository. Every CDK stack is reproducible from source. The workshop can be re-deployed at any time by running `cdk deploy --all` from `use-case-applications/cdk/`.

---

## Thank You

You have completed the ATLAS workshop — both phases.

The semantic layer is built. The agents are governed. The boundary between deterministic and probabilistic is enforced in code. The audit trail is queryable end-to-end. The two UIs serve the right data to the right personas. The Rachel Kim referral flows cleanly from signal to advisor without a hallucination anywhere in the path.

That is what governed agentic AI in a regulated industry looks like when it is built correctly.
