---
title: "Prerequisites"
weight: 5
---

# Prerequisites

Complete these steps before starting Module 1. Allow 30–45 minutes for setup.

The full rationale for each prerequisite is in `use-case-applications/spec/02-prerequisites.md`. This page focuses on the verification steps. If you encounter a failed check and need the *why*, read the spec.

## AWS Account Requirements

You need an AWS account with the following services available in **us-east-1**:

| Service | Used in | Purpose |
|---|---|---|
| Amazon SageMaker Unified Studio | All modules | Notebook execution environment |
| Amazon Neptune | All modules | Two-tier graph database from Workshop 1 |
| Amazon Bedrock | Modules 2, 3, 6, 9, 12 | LLM translation and narrative generation |
| AWS Bedrock AgentCore | Modules 3–13 | Agent Runtime invocation and registry |
| AWS AppSync | Modules 5–13 | FIBO-shaped GraphQL API |
| Amazon Cognito | Modules 6–13 | UI authentication and IDC federation |
| AWS Lake Formation | Modules 6–13 | Provisioned for data governance (per-row scoping is roadmap, not enforced) |
| Amazon CloudFront | Modules 6–13 | UI delivery |
| Amazon EventBridge | Module 6 | Advisor notification events |
| AWS Step Functions | Module 6 | Referral orchestration workflow |
| AWS IAM Identity Center | Modules 6–13 | Persona group claims |
| AWS Entity Resolution | Modules 3, 5 | Canonical URI resolution |
| Amazon ECS Fargate | Module 5 | Ontop federation runtime |
| Amazon S3 | All modules | Prompt templates and data staging |

---

## Step 1 — Confirm Workshop 1 is complete

Workshop 2 inherits the ontology, SHACL shapes, R2RML mappings, and populated Neptune deployment from Workshop 1. If any of these are missing, the pre-flight notebook (Module 1) will halt at the first failed assertion.

In your SageMaker environment:

```bash
# Quick check — confirm the SLGD endpoint is reachable and has data
cd ~/atlas/agentic-semantic-layer
python3 notebooks/shared/atlas_sparql.py --check
```

Expected output:

```
SLGD endpoint : reachable
Class count   : 22
Signal count  : ≥ 1
PASS
```

If the SLGD endpoint is not reachable, redeploy from `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` and re-run Workshop 1 modules 3 and 4 to repopulate the graph. Allow 90 minutes.

---

## Step 2 — Set up the Workshop 2 Python environment

Workshop 2 uses a separate venv managed by `uv`. Python 3.12 or newer is required.

In your terminal:

```bash
cd ~/atlas/use-case-applications
uv sync --all-groups
```

Expected output (last few lines):

```
Resolved 169 packages in NNms
Installed 169 packages in NNms
```

Register the kernel for Jupyter:

```bash
.venv/bin/python -m ipykernel install --user \
    --name atlas-workshop \
    --display-name "ATLAS Workshop 2 (Python 3.12)"
```

Verify the kernel appears:

```bash
jupyter kernelspec list | grep atlas
```

Expected output:

```
atlas-workshop   /home/sagemaker-user/.local/share/jupyter/kernels/atlas-workshop
```

If `uv` is not installed, install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env
```

---

## Step 3 — Confirm Bedrock model access

Workshop 2 uses two models:

| Model ID | Used by | Type |
|---|---|---|
| `us.anthropic.claude-sonnet-4-6` | `nl-to-sparql-agent`, `referral-rationale-drafter`, `theme-summarizer` | US cross-region inference profile |
| `amazon.titan-embed-text-v2:0` | `nl-to-sparql-agent` (embedding lookup) | Foundation model |

Verify access from your terminal:

```bash
aws bedrock-runtime invoke-model \
    --model-id us.anthropic.claude-sonnet-4-6 \
    --content-type application/json \
    --accept application/json \
    --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"Say OK"}]}' \
    /tmp/bedrock-test.json && cat /tmp/bedrock-test.json
```

Expected output (excerpt):

```json
{"content":[{"type":"text","text":"OK"}],...}
```

If this returns `AccessDeniedException`, open the Bedrock console in us-east-1 and confirm that Anthropic Claude models are enabled. The `us.` prefix (US cross-region inference profile) is required — the bare model ID will not work.

---

## Step 4 — Confirm AgentCore is reachable

Workshop 2's CDK stack provisions all AgentCore resources. Before deploying, confirm the service is available in your account:

```bash
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
```

Expected output (before Workshop 2 deploys anything):

```
{
    "agentRuntimes": []
}
```

An error about service not available means your region does not yet support AgentCore. Workshop 2 targets us-east-1.

---

## Step 5 — Create IAM Identity Center persona groups

Workshop 2's four-layer permission model begins at IAM Identity Center. Create these five groups before starting:

| Group name | Persona | UI access |
|---|---|---|
| `atlas-consumer-banker` | Consumer Banker | Wholesale UI (Phase 1) |
| `atlas-wealth-advisor` | Wealth Advisor | Wealth UI (Phase 2) |
| `atlas-bsa-analyst` | BSA Analyst | Compliance capability paths |
| `atlas-ontology-steward` | Ontology Steward | Read-only ontology and shapes |
| `atlas-auditor` | Auditor | Read-only audit trail |

In the AWS IAM Identity Center console:

1. Choose **Groups** in the left navigation
2. Choose **Create group** for each group above
3. Assign your workshop user to all five groups

For the workshop, assigning yourself to all five is correct — you will sign in as different personas to see the different capability palettes. In production, membership would be tightly scoped.

---

## Step 6 — Verify the AWS CDK CLI version

Workshop 2's CDK stack uses `@aws-cdk/aws-bedrock-agentcore-alpha` constructs, which require CDK CLI 2.1102.0 or newer.

```bash
cdk --version
```

If the output is older than `2.1102.0`:

```bash
npm install -g aws-cdk@latest
cdk --version
```

Also confirm Node.js 20 or newer is installed:

```bash
node --version
```

---

## Step 7 — Confirm Entity Resolution workflow

Workshop 1's module 5 covers Entity Resolution conceptually but may not have created the workflow in your account. Check:

1. Open the AWS Entity Resolution console
2. Confirm a matching workflow named `atlas-customer-resolution` exists
3. If it does not exist, Workshop 2's CDK stack will deploy it — you do not need to create it manually

If the workflow exists, note the workflow ARN — the pre-flight notebook will verify it is reachable.

---

## Estimated Cost

| Resource | Approximate daily cost | Notes |
|---|---|---|
| Neptune serverless (2 clusters) | ~$17/day | Inherited from Workshop 1; delete when done |
| ECS Fargate (Ontop) | ~$2/day | Deployed by Workshop 2 CDK; scales down |
| AgentCore Runtimes (12 instances) | ~$3/day | Per-invocation after minimum |
| AppSync | ~$1/day | Per-query pricing |
| CloudFront + Cognito | < $1/day | Low volume |
| Bedrock invocations | ~$5–10 total | Phase 1 + Phase 2 |

**Total for a two-day workshop run: $50–$75**

Stop the CDK-deployed resources when not in use. The cleanup module walks through `cdk destroy` to tear everything down.

---

## Verification Checklist

Before starting Module 1, confirm:

- [ ] Workshop 1 environment is reachable — `atlas_sparql.py --check` returns PASS
- [ ] `uv sync --all-groups` completed and kernel registered as `atlas-workshop`
- [ ] Bedrock test (`us.anthropic.claude-sonnet-4-6`) returns a valid response
- [ ] `bedrock-agentcore-control list-agent-runtimes` returns `[]` (or existing runtimes)
- [ ] Five IAM Identity Center groups created and workshop user assigned to all five
- [ ] CDK CLI version is 2.1102.0 or newer
- [ ] Node.js 20 or newer is installed

---

## Ready?

Proceed to [Module 1 — Pre-flight: Is Workshop 1 Ready?](../01-preflight/).
