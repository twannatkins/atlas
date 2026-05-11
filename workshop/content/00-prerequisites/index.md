---
title: "Prerequisites"
weight: 5
---

# Prerequisites

Complete these steps before starting Module 1. Allow 15–20 minutes for setup.

## AWS Account Requirements

You need an AWS account with the following services available in **us-east-1**:

| Service | Used In | Purpose |
|---------|---------|---------|
| Amazon SageMaker | All modules | Notebook execution environment |
| Amazon Neptune | Modules 3–8 | Graph database (two serverless clusters) |
| Amazon Bedrock | Modules 1, 7, 8 | LLM for ontology exploration and NL↔SPARQL |
| Amazon S3 | Modules 3–4 | Ontology staging and data lake |
| AWS CloudFormation | Module 3 | Infrastructure deployment |
| Amazon Athena | Module 4 | SQL queries over S3 data |
| AWS Glue | Module 4 | Data catalog for Iceberg tables |

## Step 1 — Create a SageMaker Notebook Instance

1. Open the [SageMaker console](https://console.aws.amazon.com/sagemaker/) in us-east-1
2. In the left navigation, choose **Notebook instances** → **Create notebook instance**
3. Configure:
   - Name: `atlas-workshop`
   - Instance type: `ml.t3.medium` (sufficient for all modules)
   - IAM role: Create a new role or select an existing one (see Step 3 below)
4. Under **Git repositories**, add:
   - Repository: `https://github.com/twannatkins/atlas.git`
   - Branch: `main`
5. Choose **Create notebook instance**
6. Wait for status to change to **InService** (2–3 minutes)

Alternatively, if using **SageMaker Studio**, create a JupyterLab space and clone
the repository from the terminal.

## Step 2 — Enable Amazon Bedrock Model Access

1. Open the [Bedrock console](https://console.aws.amazon.com/bedrock/) in us-east-1
2. In the left navigation, choose **Model access**
3. Choose **Manage model access**
4. Enable access to **Anthropic → Claude 3.5 Sonnet** (or later)
5. Choose **Save changes**
6. Wait for status to show **Access granted** (1–2 minutes)

The workshop uses the cross-region inference profile `us.anthropic.claude-sonnet-4-6`.
This is available automatically once Anthropic Claude access is granted.

## Step 3 — Configure IAM Permissions

The SageMaker execution role needs these managed policies:

- `AmazonSageMakerFullAccess`
- `AmazonS3FullAccess`
- `NeptuneFullAccess`
- `AmazonAthenaFullAccess`
- `AWSGlueServiceRole`
- `AWSCloudFormationFullAccess`

Plus this inline policy for Bedrock access:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ],
    "Resource": "arn:aws:bedrock:*::foundation-model/*"
  }]
}
```

To add the inline policy:

1. Open the [IAM console](https://console.aws.amazon.com/iam/)
2. Find your SageMaker execution role (named like `AmazonSageMaker-ExecutionRole-*`)
3. Choose **Add permissions** → **Create inline policy**
4. Switch to the **JSON** tab and paste the policy above
5. Name it `bedrock-invoke` and choose **Create policy**

## Step 4 — Note Your VPC and Subnet IDs

You will need these in Module 3 when deploying Neptune clusters.

1. Open the [VPC console](https://console.aws.amazon.com/vpc/)
2. In the left navigation, choose **Your VPCs**
3. Record your VPC ID (e.g., `vpc-0abc123def456`)
4. Record your VPC CIDR block (e.g., `10.0.0.0/16`)
5. Choose **Subnets** in the left navigation
6. Record at least **two subnet IDs** that are in **different Availability Zones**
   (e.g., `subnet-aaa` in us-east-1a and `subnet-bbb` in us-east-1b)

If you do not have a VPC, the default VPC in us-east-1 works. Every AWS account
has a default VPC with subnets in each AZ.

## Step 5 — Install Python Dependencies

Open a terminal in your SageMaker notebook instance and run:

```bash
cd ~/SageMaker/atlas
pip install -r notebooks/shared/requirements.txt
```

This installs: `rdflib`, `pyshacl`, `boto3`, `requests`, `pandas`, `pyarrow`, `faker`.

## Python Version

This workshop requires **Python 3.10 or later**. SageMaker notebook instances and
SageMaker Studio ship with Python 3.10+ by default. Verify with:

```bash
python3 --version
```

## Estimated Cost

| Resource | Approximate Cost | Notes |
|----------|-----------------|-------|
| Neptune serverless (2 clusters) | ~$17/day | Scales to zero when idle |
| SageMaker notebook (ml.t3.medium) | ~$0.05/hr | Stop when not in use |
| Bedrock invocations | ~$1–3 total | Modules 1, 7, 8 |
| S3 + Athena + Glue | < $0.50 | Minimal data volume |

**Total for a single workshop run (5–6 hours): $10–$18**

**Important:** Delete the CloudFormation stack when you are done. Neptune clusters
cost ~$17/day if left running. Module 99 (Cleanup) walks you through teardown.

## Verification Checklist

Before starting Module 1, confirm:

- [ ] SageMaker notebook instance is **InService**
- [ ] Repository is cloned (you can see `notebooks/` in the file browser)
- [ ] `pip install -r notebooks/shared/requirements.txt` completed without errors
- [ ] Bedrock model access shows **Access granted** for Anthropic Claude
- [ ] You have your VPC ID, CIDR, and two subnet IDs written down
- [ ] You understand the cost (~$17/day for Neptune if left running)

## Ready?

Proceed to [Module 1 — From Business Question to Ontology](../01-from-business-question/).
