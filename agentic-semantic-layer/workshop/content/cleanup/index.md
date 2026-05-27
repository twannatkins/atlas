---
title: "Cleanup"
weight: 99
---

# Cleanup — Tear Down Workshop Infrastructure

## Why Cleanup Matters

The two Neptune serverless clusters cost approximately **$17 per day combined**
when running at minimum capacity. If you are done with the workshop, delete the
infrastructure to stop charges.

## Step 1 — Delete the CloudFormation Stack

This removes both Neptune clusters, the S3 bucket, the IAM role, and the security group.

### Option A: AWS Console

1. Open the [CloudFormation console](https://console.aws.amazon.com/cloudformation/) in us-east-1
2. Select the stack named `atlas-neptune-twotier`
3. Choose **Delete**
4. Confirm deletion
5. Wait for status to show `DELETE_COMPLETE` (5–10 minutes)

### Option B: AWS CLI

```bash
aws cloudformation delete-stack \
  --stack-name atlas-neptune-twotier \
  --region us-east-1
```

Wait for deletion to complete:

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name atlas-neptune-twotier \
  --region us-east-1
```

## Step 2 — Stop or Delete the SageMaker Notebook Instance

If you created a notebook instance for this workshop:

1. Open the [SageMaker console](https://console.aws.amazon.com/sagemaker/)
2. Choose **Notebook instances**
3. Select `atlas-workshop`
4. Choose **Stop** (to preserve your work) or **Delete** (to remove entirely)

A stopped notebook instance incurs no compute charges but retains its storage volume
(~$0.10/GB/month for the EBS volume).

## Step 3 — Verify No Resources Remain

Check for any remaining resources:

```bash
# Check for Neptune clusters
aws neptune describe-db-clusters --region us-east-1 \
  --query "DBClusters[?contains(DBClusterIdentifier, 'atlas')]"

# Check for S3 buckets
aws s3 ls | grep atlas-ontology

# Check for the IAM role
aws iam get-role --role-name atlas-neptune-s3-access 2>/dev/null
```

All three commands should return empty results or "not found" errors.

## Step 4 — (Optional) Remove Bedrock Model Access

If you enabled Bedrock model access only for this workshop and do not plan to use
it again:

1. Open the [Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Choose **Model access** → **Manage model access**
3. Deselect Anthropic Claude models
4. Choose **Save changes**

This is optional — Bedrock model access does not incur charges when not in use.

## Cost Summary

If you completed the workshop in a single session (5–6 hours) and cleaned up
immediately afterward, your total cost should be approximately **$10–$18**.

If you left the Neptune clusters running overnight, add ~$17 per day.

## What You Built

Over the course of this workshop, you built:

| Layer | What | Where |
|-------|------|-------|
| Ontology | 24-class FIBO-aligned ontology (19 core + 3 FIBO + 2 governance) with 6 SHACL shapes | `ontology/` |
| Infrastructure | Two-tier Neptune (LGD + SLGD) | CloudFormation (now deleted) |
| Data Integration | Three connection patterns (Iceberg, Athena, Lambda) | `mappings/` |
| Application | NL↔SPARQL, bounded agent, human-in-the-loop | Notebooks 7–8 |
| Governance | PROV-O provenance, promotion path, audit trail | Notebooks 5–8 |

The code, ontology, mappings, and documentation remain in this repository.
You can redeploy the infrastructure at any time by re-running the CloudFormation
stack from Module 3.

## Thank You

You have completed the ATLAS workshop. The architecture is defensible, the boundary
is enforced in code, and the audit trail is queryable end-to-end.
