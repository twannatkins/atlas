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
   - For project profile, choose **All capabilities** (this gives you JupyterLab,
     terminal access, and VPC network connectivity needed for Neptune)
4. Choose **Create project**
5. Wait for the project to be created (1–2 minutes)
6. Click into your new `atlas-workshop` project

> **The one rule that makes the rest work: Neptune must live in the *same* VPC as your
> Studio kernel.** An "All capabilities" Unified Studio project runs its notebook kernels
> inside a DataZone-managed VPC. In Module 3 you deploy Neptune into a VPC of your choosing —
> and if that is *not* the VPC your Studio kernel runs in, the load step fails with Neptune
> unreachable on port 8182 and no obvious cause. This workshop's proven path (the one the
> authors ran) is **Path A: let Studio create its VPC, then deploy Neptune into that same
> VPC.** Step 4 below shows you how to find that VPC's ID. (A clean-account alternative —
> building the VPC first and putting Studio into it — is **Path B**, covered in Step 4
> Option B with an honest caveat about what has and hasn't been proven.)

### 1c. Open a JupyterLab Notebook Environment

From inside your project:

1. Choose **Create a notebook** (or look for a JupyterLab/Notebook option in the
   project sidebar)
2. This provisions a **space** — a compute environment for your notebooks
3. Accept the defaults or configure:
   - Instance: `ml.t3.medium` (sufficient for all modules)
   - Image: **SageMaker Distribution 3.9** (or latest — includes Python 3.11+)
   - Storage: 16 GB (default is fine)
4. Choose **Create** or **Run**
5. Wait for the "Connecting to space" screen to finish (1–3 minutes)
6. Once connected, you'll see a JupyterLab interface with a file browser on the
   left and a Launcher tab on the right

### 1d. Clone the Workshop Repository

1. In JupyterLab, choose **File → New → Terminal** (or click the Terminal icon
   in the Launcher)
2. In the terminal, run:

```bash
git clone https://github.com/twannatkins/atlas.git
```

3. The repository is now at `~/atlas/`. Dependencies are installed automatically
   when you run the first cell of each notebook — no manual `pip install` needed.

> **Why automatic install?** SageMaker Unified Studio's `project.python` kernel
> runs in its own Python environment, separate from the JupyterLab terminal.
> Running `pip install` in the terminal installs packages into the terminal Python,
> not the kernel. Each notebook's first code cell uses `sys.executable` to install
> into the correct kernel environment and skips packages already at the right version.
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

Unified Studio (DataZone-backed) does not expose a single "Execution role" field the way a
classic SageMaker domain does — it uses a **DataZone-managed role** with a non-standard name
pattern (e.g. `datazone_usr_role_…`), and the role your *kernel* runs as is the one that
matters. The reliable way to identify it is to ask from inside the running environment:

```bash
# Run this in your JupyterLab terminal — it prints the exact role ARN the kernel runs as
aws sts get-caller-identity --query Arn --output text
```

The ARN it prints (its `…role/<name>/…` segment) is the execution role to attach policies
to below.

> **Two-role caveat (account-specific).** A Unified Studio domain may carry **two**
> DataZone-managed roles — a domain-default role and the kernel-running role. The command
> above returns the one the kernel actually uses, which is the one that must receive every
> permission. If a later notebook cell still gets a 403 after you attach a policy, you have
> likely patched the wrong role — re-run the command from a *notebook cell* (not just the
> terminal) to confirm the kernel's role and attach there too.

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

> **Note:** After deploying the Neptune clusters in Module 3, you will also
> attach the `atlas-neptune-iam-auth` managed policy (exported by the
> CloudFormation stack). This grants SigV4-authenticated access to the
> specific Neptune clusters rather than the broad `NeptuneFullAccess` policy.
> For the workshop, both are attached; in production, only the scoped policy
> would be used.

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

## Step 4 — Get the VPC your Neptune will share with Studio (and note its IDs)

Module 3 deploys the Neptune clusters into a VPC, and you will pass that VPC's id, its
CIDR, and at least **two subnet IDs in different Availability Zones** as parameters. The
non-negotiable constraint (from Step 1): **that VPC must be the one your Studio kernel runs
in**, or the notebooks cannot reach Neptune on port 8182. Choose the path that fits your
account.

### Path A — Use your Unified Studio project's VPC (the proven path)

When you created the "All capabilities" project in Step 1, Unified Studio created a
DataZone-managed VPC and runs your notebook kernels inside it. Deploy Neptune into **that
same VPC** and the in-VPC kernel reaches it directly. This is the path the workshop authors
ran end to end, so it is the one to prefer.

**Find that VPC's ID — programmatically, not from the console.** The SageMaker console does
*not* surface a Unified Studio domain's VPC the way it does for a classic domain (a VpcOnly
Unified Studio domain often shows no VPC at all in `describe-domain` output), so the old
"Domains → Network → VPC" console lookup does not work here. Instead, run this from your
JupyterLab terminal (after Step 1), which queries the domain directly:

```bash
# List your Studio domains, then read the VPC + subnets the domain runs in
aws sagemaker list-domains --region us-east-1 \
  --query 'Domains[].{Name:DomainName,Id:DomainId}' --output table

# Using the DomainId from above:
aws sagemaker describe-domain --region us-east-1 --domain-id <your-domain-id> \
  --query '{VpcId:VpcId,Subnets:SubnetIds}' --output json
```

Record the **VpcId** and the **SubnetIds** it prints (you need at least two in different
AZs). Get the CIDR for that VPC with:

```bash
aws ec2 describe-vpcs --region us-east-1 --vpc-ids <your-vpc-id> \
  --query 'Vpcs[0].CidrBlock' --output text
```

These are the exact `VpcId` / `SubnetIds` / `VpcCidr` you pass to Module 3. Because they are
the VPC Studio already runs in, the load step in Module 3 reaches Neptune with no extra
networking.

### Path B — Build the foundation VPC first, and put Studio in it (clean-account alternative)

If you are starting from a **clean account** with no Unified Studio VPC to share, build one
with **[Module 0 — The Foundation Network](../00-foundation/)** *before* Module 1. Module 0
deploys `agentic-semantic-layer/infrastructure/atlas-foundation.yaml` — a minimal VPC with
two private subnets in **AgentCore-supported AZs** (it deliberately excludes `us-east-1b`,
a constraint Workshop 2's agent runtimes depend on) — and outputs the exact
`VpcId` / `PrivateSubnetIds` / `VpcCidr` you then paste into Module 3. The full teaching is
in [`notebooks/00_foundation.ipynb`](../../../notebooks/00_foundation.ipynb).

> **Honest status — Path B is dry-validated, not live-proven.** The foundation template is
> `cfn-lint` clean, `validate-template` valid, and change-set previewed — config-verified.
> But the **critical seam on this path has not been proven end to end**: you must also place
> your Studio domain *into* this VPC (VpcOnly, in its two private subnets) so the kernel and
> Neptune share it — and that Studio-into-the-foundation-VPC placement is the step the
> authors did *not* run live. Path A (above) is the proven one. Treat Path B as the
> structurally-sound clean-account design, and expect to confirm the Studio placement
> yourself. The same VPC-sharing rule applies either way: the kernel must run in Neptune's
> VPC.

Either way, by the end of this step you have a **VpcId, a VpcCidr, and two subnet IDs in
two different AZs** — the VPC your Studio kernel runs in — written down for Module 3.

---

## Step 5 — Verify Your Setup

In your JupyterLab terminal, check Python version and AWS connectivity:

```bash
# Check Python version (must be 3.10+)
python3 --version

# Check AWS credentials are active
aws sts get-caller-identity --query Account --output text
```

Expected output:

```
Python 3.10.x (or higher)
123456789012
```

(the 12-digit number is your own AWS account ID)

Package dependencies (`rdflib`, `pyshacl`, `pandas`, etc.) are verified
automatically when you run the first cell of each notebook. You do not need
to check them manually here.

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
- [ ] You have the VPC ID, CIDR, and two subnet IDs **of the VPC your Studio kernel runs in** written down (Path A: discovered via `describe-domain`; Path B: the foundation VPC, with Studio placed into it)
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
