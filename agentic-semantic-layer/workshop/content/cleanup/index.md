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

## Step 2 — Stop or Delete the SageMaker Unified Studio Project

This workshop ran inside a SageMaker Unified Studio project named `atlas-workshop`
(created in the Prerequisites step). The running JupyterLab environment inside that
project accrues compute charges while it is running, so stop or delete it when you
are done.

**To stop compute charges but keep your work:**

1. Open the [SageMaker console](https://console.aws.amazon.com/sagemaker/) → **Studio**
2. Open the `atlas-workshop` project
3. Stop any running JupyterLab or notebook apps (look for running spaces/apps in
   the project and shut them down)

Stopping the running apps stops the hourly compute charge while leaving the project
and your notebooks in place, so you can return later by restarting the app.

**To remove everything:**

1. From the SageMaker Studio project list, select `atlas-workshop`
2. Delete the project (this removes the JupyterLab environment and associated
   compute resources)

You can leave the SageMaker Unified Studio **domain** in place — a domain with no
running apps incurs no compute charges.

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

You have completed the ATLAS workshop. You built a working reference implementation
of the three-layer architecture on a synthetic dataset, with the boundary mechanisms
operational (Module 6 SHACL shapes and Module 7's `atlas_sparql.validate()` pre-check)
and the audit trail queryable end-to-end in SPARQL.

Moving from this reference implementation to production requires real data via the
R2RML mappings, a real scoring model in Module 8's place, and the operational
processes around the human-in-the-loop step. The mechanisms you built here are the
load-bearing pieces — the rest is configuration, integration, and operational
discipline.
