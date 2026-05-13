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
| Amazon SageMaker Unified Studio | All modules | Notebook execution environment |
| Amazon Neptune | Modules 3–8 | Graph database (two serverless clusters) |
| Amazon Bedrock | Modules 1, 7, 8 | LLM for ontology exploration and NL↔SPARQL |
| Amazon S3 | Modules 3–4 | Ontology staging and data lake |
| AWS CloudFormation | Module 3 | Infrastructure deployment |
| Amazon Athena | Module 4 | SQL queries over S3 data |
| AWS Glue | Module 4 | Data catalog for Iceberg tables |

---

## Step 1 — Set Up SageMaker Unified Studio

This workshop runs inside **Amazon SageMaker Unified Studio** using a JupyterLab
notebook environment. SageMaker Unified Studio organizes work into **projects** —
you'll create a project first, then open a notebook environment inside it.

### 1a. Open SageMaker Unified Studio

1. Open the [Amazon SageMaker console](https://console.aws.amazon.com/sagemaker/) in **us-east-1**
2. Choose **Studio** to open SageMaker Unified Studio
3. If this is your first time, you may be prompted to set up a domain — follow the
   guided setup (choose defaults for a single-user environment)

### 1b. Create a Project

SageMaker Unified Studio requires a **project** before you can create notebooks or
other resources. A project is a container for your work.

1. In the Studio home page, choose **Projects** in the left sidebar
2. Choose **Create project**
3. Configure:
   - Project name: `atlas-workshop`
   - Description: `ATLAS FSI Semantic Layer Workshop`
   - For project template/profile, choose a default data science or ML template
     (any template that includes JupyterLab/notebook support works)
4. Choose **Create project**
5. Wait for the project to be created (1–2 minutes)
6. Click into your new `atlas-workshop` project

### 1c. Open a JupyterLab Notebook Environment

From inside your project:

1. In the project sidebar, look for **IDE** or **Notebooks** (depending on your
   Studio version)
2. Choose **JupyterLab** to open a notebook environment
   - If prompted for compute, choose `ml.t3.medium` (sufficient for all modules)
   - If prompted for an image, choose **SageMaker Distribution 2.x** (includes
     Python 3.10+, pandas, boto3)
3. Wait for the environment to start (1–2 minutes)
4. You should now see a JupyterLab interface with a file browser on the left and
   a Launcher tab on the right

### 1d. Clone the Workshop Repository

1. In JupyterLab, choose **File → New → Terminal** (or click the Terminal icon
   in the Launcher)
2. In the terminal, run:

```bash
git clone https://github.com/twannatkins/atlas.git
cd atlas
pip install -r notebooks/shared/requirements.txt
```

3. Wait for the install to complete (30–60 seconds)
4. In the left file browser, click the folder icon to refresh, then navigate into
   the `atlas/` folder. You'll see: `notebooks/`, `ontology/`, `data/`,
   `infrastructure/`, etc.

### 1e. Open Your First Notebook

1. In the file browser, navigate to `atlas/notebooks/`
2. Double-click `01_journey_to_ontology.ipynb`
3. If prompted to select a kernel, choose **Python 3 (ipykernel)**
4. You should see the Module 1 notebook open with markdown and code cells

**You are now ready to run the workshop.** Each module is a notebook in this folder,
numbered 01 through 08. Run them in order.

---

## Step 2 — Confirm Amazon Bedrock Access

Module 1 uses Bedrock for a Socratic exploration exercise. As of 2025, **Bedrock
foundation models are automatically enabled** — you no longer need to manually
activate model access.

> **Note:** The Model access page in the Bedrock console has been retired.
> Serverless foundation models are now automatically enabled across all AWS
> commercial regions when first invoked in your account.

**For first-time Anthropic users:** You may be prompted to submit use case details
before accessing Claude models. If this happens:

1. Open the [Bedrock console](https://console.aws.amazon.com/bedrock/) in us-east-1
2. Choose **Model catalog** in the left navigation
3. Find **Anthropic Claude** and attempt to open it in the Playground
4. If prompted, submit the required use case details
5. Access is typically granted within minutes

**To verify access works**, run this in your JupyterLab terminal (after Step 1):

```bash
cd ~/atlas
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
result = json.loads(resp['body'].read())
print('Bedrock: OK -', result['content'][0]['text'])
"
```

If this prints `Bedrock: OK`, you're set. If it fails with `AccessDeniedException`,
check the IAM permissions in Step 3 below.

---

## Step 3 — Configure IAM Permissions

The SageMaker execution role (associated with your Studio domain or project) needs
additional permissions for Neptune, CloudFormation, and Bedrock.

### Find your execution role

1. In the SageMaker console, choose **Domains** in the left navigation
2. Click your domain name
3. Look for the **Execution role** ARN (looks like
   `arn:aws:iam::XXXX:role/AmazonSageMaker-ExecutionRole-XXXX` or similar)

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

**Important:** The VPC your SageMaker Studio domain uses must be the same VPC where
you deploy Neptune. If they're in different VPCs, the notebooks won't be able to
connect to Neptune on port 8182. To check which VPC Studio uses: SageMaker console →
Domains → your domain → look for "VPC" in the Network section.

---

## Step 5 — Verify Your Setup

In your JupyterLab terminal, run these checks:

```bash
cd ~/atlas

# Check Python version (must be 3.10+)
python3 --version

# Check key packages installed
python3 -c "import rdflib; print(f'rdflib: {rdflib.__version__}')"
python3 -c "import pyshacl; print(f'pyshacl: {pyshacl.__version__}')"
python3 -c "import boto3; print(f'boto3: {boto3.__version__}')"
python3 -c "import pandas; print(f'pandas: {pandas.__version__}')"
```

Expected output:

```
Python 3.10.x (or higher)
rdflib: 7.0.0
pyshacl: 0.25.0
boto3: 1.34.x (or higher)
pandas: 2.x.x
```

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
- **Stop your JupyterLab environment** in Studio to stop compute charges
- **Delete the CloudFormation stack** if you're done with Modules 3–8
  (Neptune costs ~$17/day if left running)

---

## Verification Checklist

Before starting Module 1, confirm:

- [ ] SageMaker Studio project created and JupyterLab environment is running
- [ ] Repository is cloned (`atlas/` folder visible in file browser)
- [ ] `pip install` completed without errors
- [ ] `python3 --version` shows 3.10 or higher
- [ ] Bedrock test prints `Bedrock: OK` (or you've confirmed Anthropic access)
- [ ] You have your VPC ID, CIDR, and two subnet IDs written down
- [ ] You understand the cost (~$17/day for Neptune if left running)

---

## Quick Reference: Navigating JupyterLab

| Task | How |
|------|-----|
| Open a notebook | File browser (left sidebar) → double-click the `.ipynb` file |
| Run a cell | Click the cell, then press **Shift+Enter** (or the ▶ button) |
| Run all cells | **Run** menu → **Run All Cells** |
| Open a terminal | **File** → **New** → **Terminal** |
| Restart kernel | **Kernel** menu → **Restart Kernel** |
| Stop compute | Back in Studio → stop your JupyterLab environment |

---

## Ready?

Proceed to [Module 1 — From Business Question to Ontology](../01-from-business-question/).
