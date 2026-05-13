---
title: "Prerequisites"
weight: 5
---

# Prerequisites

Complete these steps before starting Module 1. Allow 20–30 minutes for setup.

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

---

## Step 1 — Open SageMaker Studio and Create a JupyterLab Space

This workshop runs inside **Amazon SageMaker Studio** using a JupyterLab notebook
environment. If you already have a SageMaker Studio domain, skip to step 1c.

### 1a. Open SageMaker Studio

1. Open the [Amazon SageMaker console](https://console.aws.amazon.com/sagemaker/) in **us-east-1**
2. In the left navigation, choose **Studio** (under Admin configurations, or directly from the landing page)
3. If you see a domain listed, choose **Open Studio** next to your user profile
4. If no domain exists, choose **Set up for single user** — this creates a domain
   with default settings (takes 2–3 minutes)

You should now see the **SageMaker Studio home page** with a left sidebar showing
Applications, Spaces, and other options.

### 1b. Create a JupyterLab Space

A "Space" in SageMaker Studio is an isolated environment where your notebooks run.

1. In the Studio left sidebar, choose **JupyterLab**
2. Choose **Create JupyterLab space**
3. Name it: `atlas-workshop`
4. Choose **Create space**
5. On the space configuration page:
   - Instance type: `ml.t3.medium` (sufficient for all modules)
   - Image: **SageMaker Distribution 2.x** (includes Python 3.10+, pandas, boto3)
   - Storage: 5 GB (default is fine)
6. Choose **Run space**
7. Wait for status to show **Running** (1–2 minutes)
8. Choose **Open JupyterLab**

You should now see a JupyterLab interface with a file browser on the left and a
Launcher tab on the right.

### 1c. Clone the Workshop Repository

1. In JupyterLab, choose **File → New → Terminal** (or click the Terminal icon in the Launcher)
2. In the terminal, run:

```bash
cd ~
git clone https://github.com/twannatkins/atlas.git
cd atlas
pip install -r notebooks/shared/requirements.txt
```

3. Wait for the install to complete (30–60 seconds)
4. In the left file browser, you should now see the `atlas/` folder. Click into it.
   You'll see: `notebooks/`, `ontology/`, `data/`, `infrastructure/`, etc.

### 1d. Open Your First Notebook

1. In the file browser, navigate to `atlas/notebooks/`
2. Double-click `01_journey_to_ontology.ipynb`
3. If prompted to select a kernel, choose **Python 3 (ipykernel)**
4. You should see the Module 1 notebook open with markdown and code cells

**You are now ready to run the workshop.** Each module is a notebook in this folder,
numbered 01 through 08. Run them in order.

---

## Step 2 — Enable Amazon Bedrock Model Access

Module 1 uses Bedrock for a Socratic exploration exercise. Enable it now so you
don't hit a permissions error mid-module.

1. Open a **new browser tab** (keep SageMaker Studio open)
2. Go to the [Bedrock console](https://console.aws.amazon.com/bedrock/) in us-east-1
3. In the left navigation, choose **Model access**
4. Choose **Manage model access**
5. Find **Anthropic** in the list and check the box next to **Claude 3.5 Sonnet** (or later versions)
6. Choose **Save changes**
7. Wait for status to show **Access granted** (1–2 minutes)

The workshop uses the cross-region inference profile `us.anthropic.claude-sonnet-4-6`.
This is available automatically once Anthropic Claude access is granted.

---

## Step 3 — Configure IAM Permissions

The SageMaker execution role (automatically created with your domain/space) needs
additional permissions for Neptune, CloudFormation, and Bedrock.

### Find your execution role

1. In the SageMaker console, choose **Domains** in the left navigation
2. Click your domain name
3. Click your user profile
4. Note the **Execution role** ARN (looks like `arn:aws:iam::XXXX:role/AmazonSageMaker-ExecutionRole-XXXX`)

### Add managed policies

1. Open the [IAM console](https://console.aws.amazon.com/iam/) in a new tab
2. Choose **Roles** in the left navigation
3. Search for your execution role name (the part after `role/`)
4. Click the role name to open it
5. Choose **Add permissions** → **Attach policies**
6. Search for and attach each of these:
   - `AmazonS3FullAccess`
   - `NeptuneFullAccess`
   - `AmazonAthenaFullAccess`
   - `AWSGlueServiceRole`
   - `AWSCloudFormationFullAccess`
7. Choose **Add permissions**

### Add Bedrock inline policy

1. Still on the role page, choose **Add permissions** → **Create inline policy**
2. Choose the **JSON** tab
3. Paste this policy:

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

4. Choose **Next**
5. Name it `bedrock-invoke`
6. Choose **Create policy**

---

## Step 4 — Note Your VPC and Subnet IDs

You will need these in Module 3 when deploying Neptune clusters. Neptune must be
in the same VPC as your SageMaker Studio domain so the notebooks can reach it.

1. Open the [VPC console](https://console.aws.amazon.com/vpc/) in a new tab
2. In the left navigation, choose **Your VPCs**
3. Record your **VPC ID** (e.g., `vpc-0abc123def456`)
4. Record your **VPC CIDR block** (e.g., `10.0.0.0/16`) — shown in the IPv4 CIDR column
5. Choose **Subnets** in the left navigation
6. Filter by your VPC ID
7. Record at least **two subnet IDs** that are in **different Availability Zones**
   (check the "Availability Zone" column — you need subnets in at least 2 different AZs)

**Tip:** If you're using the default VPC, it already has subnets in every AZ.
Your SageMaker Studio domain is likely already in this VPC.

**Important:** The VPC your SageMaker Studio domain uses must be the same VPC where
you deploy Neptune. If they're in different VPCs, the notebooks won't be able to
connect to Neptune. To check which VPC Studio uses: SageMaker console → Domains →
your domain → look for "VPC" in the Network section.

---

## Step 5 — Verify Your Setup

Back in your JupyterLab terminal (inside SageMaker Studio), run these checks:

```bash
cd ~/atlas

# Check Python version (must be 3.10+)
python3 --version

# Check key packages installed
python3 -c "import rdflib; print(f'rdflib: {rdflib.__version__}')"
python3 -c "import pyshacl; print(f'pyshacl: {pyshacl.__version__}')"
python3 -c "import boto3; print(f'boto3: {boto3.__version__}')"
python3 -c "import pandas; print(f'pandas: {pandas.__version__}')"

# Check Bedrock access
python3 -c "
import boto3, json
client = boto3.client('bedrock-runtime', region_name='us-east-1')
resp = client.invoke_model(
    modelId='us.anthropic.claude-sonnet-4-6',
    contentType='application/json',
    accept='application/json',
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 10,
        'messages': [{'role': 'user', 'content': 'Say OK'}]
    })
)
print('Bedrock: OK')
"
```

Expected output:

```
Python 3.10.x (or higher)
rdflib: 7.0.0
pyshacl: 0.25.0
boto3: 1.34.x (or higher)
pandas: 2.x.x
Bedrock: OK
```

If the Bedrock check fails with `AccessDeniedException`, revisit Step 3 (IAM policy)
and Step 2 (model access).

---

## Estimated Cost

| Resource | Approximate Cost | Notes |
|----------|-----------------|-------|
| Neptune serverless (2 clusters) | ~$17/day | Scales to zero when idle |
| SageMaker Studio (ml.t3.medium) | ~$0.05/hr | Stop the space when not in use |
| Bedrock invocations | ~$1–3 total | Modules 1, 7, 8 |
| S3 + Athena + Glue | < $0.50 | Minimal data volume |

**Total for a single workshop run (5–6 hours): $10–$18**

**Important:** When you're done for the day:
- **Stop your JupyterLab space** (Studio → JupyterLab → your space → Stop)
- **Delete the CloudFormation stack** if you're done with Modules 3–8
  (Neptune costs ~$17/day if left running)

---

## Verification Checklist

Before starting Module 1, confirm:

- [ ] SageMaker Studio JupyterLab space is **Running** and open
- [ ] Repository is cloned (`atlas/` folder visible in file browser)
- [ ] `pip install` completed without errors
- [ ] `python3 --version` shows 3.10 or higher
- [ ] Bedrock test prints `Bedrock: OK`
- [ ] You have your VPC ID, CIDR, and two subnet IDs written down
- [ ] You understand the cost (~$17/day for Neptune if left running)

---

## Quick Reference: Navigating SageMaker Studio JupyterLab

| Task | How |
|------|-----|
| Open a notebook | File browser (left sidebar) → double-click the `.ipynb` file |
| Run a cell | Click the cell, then press **Shift+Enter** (or the ▶ button) |
| Run all cells | **Run** menu → **Run All Cells** |
| Open a terminal | **File** → **New** → **Terminal** |
| Restart kernel | **Kernel** menu → **Restart Kernel** |
| Stop your space | Back in Studio home → JupyterLab → click **Stop** on your space |
| Check running spaces | Studio home → JupyterLab → shows status of all spaces |

---

## Ready?

Proceed to [Module 1 — From Business Question to Ontology](../01-from-business-question/).
