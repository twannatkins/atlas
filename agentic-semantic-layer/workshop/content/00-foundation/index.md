---
title: "Module 0 — The Foundation Network (optional)"
weight: 8
---

# Module 0 — The Foundation Network

## Learning Objectives

- Explain why the ATLAS workshops assume a VPC already exists, and what that VPC must
  contain for Workshop 1's Neptune stack and Workshop 2's CDK to consume it
- Deploy the minimal foundation network (`atlas-foundation.yaml`) when you do not already
  have a suitable VPC, and capture its `VpcId` / `PrivateSubnetIds` / `VpcCidr` outputs
- Understand the **AZ-exclusion rule** — why the private subnets must avoid `us-east-1b`
  (AZ-ID `use1-az6`), which Amazon Bedrock AgentCore VPC mode does not support — and how the
  template makes selecting it structurally impossible
- State honestly what "dry-validated" means: config-verified, not yet live-proven

## Time Estimate

15–20 minutes (skip entirely if you already have a suitable VPC — see Prerequisites Option A).

## Prerequisites

- [Prerequisites](../00-prerequisites/) Steps 1–3 complete (Studio, Bedrock, IAM)
- This module is **Option B** from Prerequisites Step 4: run it only if you are starting from
  a clean account or do not have a VPC with two private subnets in two different AZs. If you
  have one, use it (Option A) and skip to [Module 1](../01-from-business-question/).

## What You Will Build

A single CloudFormation stack — a VPC with two private subnets in AgentCore-supported AZs, a
public subnet, a NAT gateway + Elastic IP, an internet gateway, and the route tables that
wire them — and nothing more. Its three outputs (`VpcId`, `PrivateSubnetIds`, `VpcCidr`) are
the exact inputs Module 3's Neptune stack and Workshop 2's CDK consume.

The notebook is [`notebooks/00_foundation.ipynb`](../../../notebooks/00_foundation.ipynb); the
template is `infrastructure/atlas-foundation.yaml`. This page is the runner-facing module
page — open the notebook for the full teaching (the traceability table, the change-set
preview, the output-contract cross-check).

## Why a bring-your-own foundation

ATLAS does not ship a bespoke production VPC. The foundation the workshop authors run on is
an existing SageMaker Studio VPC — a network that already happened to be there, which is the
normal case in a real institution. So Module 0 does not templatize a specific ATLAS VPC
(there isn't one); it builds the **equivalent minimal foundation** a customer needs when they
do not already have a suitable VPC, at a clean CIDR, with the one non-obvious correctness
constraint baked in. Every resource traces to a concrete Workshop 1 or Workshop 2
requirement; nothing untraceable (no VPC endpoints, no Transit Gateway, no flow logs) is
included. The notebook's traceability table shows each construct mapped to its consumer.

## The AZ-exclusion lesson

This is the single most valuable thing in Module 0. Amazon Bedrock AgentCore VPC mode — used
by Workshop 2's agent runtimes — can only place its network interfaces in a *subset* of
Availability Zones. In `us-east-1` the supported zones are the **AZ-IDs** `use1-az1`,
`use1-az2`, and `use1-az4`. It does **not** support `use1-az6`.

AZ *names* (`us-east-1a`…`f`) are shuffled per account, but AZ *IDs* (`use1-azN`) are stable.
So the unsupported zone is reliably `use1-az6` — and *which name* it wears varies by account.
If a private subnet lands there, Workshop 1 still works (Neptune doesn't care), and then, much
later, Workshop 2's AgentCore runtimes fail to place their ENIs with a confusing,
far-downstream error. `atlas-foundation.yaml` prevents this structurally: it selects the
private subnets by `AvailabilityZoneId` constrained to `[use1-az1, use1-az2, use1-az4]`, so
`use1-az6` is not a selectable value. This is the same rule Workshop 2's
`networking.ts` encodes downstream — Module 0 moves it upstream, into the network's creation.

## Steps

### Step 1 — Open the notebook and inspect the template

Open [`notebooks/00_foundation.ipynb`](../../../notebooks/00_foundation.ipynb) in SageMaker
Studio. Read the concept, the traceability table, and the AZ-exclusion section, then run the
inspection cell — it lists the 15 resources the template declares and confirms it is
`cfn-lint`-clean and accepted by `aws cloudformation validate-template`.

### Step 2 — Confirm the AZ mapping for your account

Run the AZ-mapping cell. It prints this account's AZ-name → AZ-ID mapping and flags the
AgentCore-unsupported zone (`use1-az6`), so you can see which *name* to avoid. The template's
`AllowedValues` already enforces the rule; this cell makes it visible.

### Step 3 — Deploy the foundation

When you are ready to create the network (in your account), deploy the template, choosing two
supported, distinct AZ-IDs (defaults are `use1-az1` / `use1-az2`):

```bash
aws cloudformation deploy \
  --template-file agentic-semantic-layer/infrastructure/atlas-foundation.yaml \
  --stack-name atlas-foundation \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides VpcCidr=10.0.0.0/16 PrivateSubnet1AzId=use1-az1 PrivateSubnet2AzId=use1-az2
```

### Step 4 — Capture the outputs

```bash
aws cloudformation describe-stacks --stack-name atlas-foundation \
  --query 'Stacks[0].Outputs' --output table
```

Record `VpcId`, `PrivateSubnetIds`, and `VpcCidr`. These feed
[Module 3 — Two-Tier Neptune](../03-two-tier-neptune/) (its `VpcId` / `SubnetIds` / `VpcCidr`
parameters) and, later, Workshop 2's `cdk.json` context.

## Expected Outputs

- `cfn-lint` clean and `validate-template` valid (config-verified)
- The change-set preview lists 15 resources, all `Add` (a VPC, three subnets, an internet
  gateway + attachment, a NAT gateway + EIP, two route tables, two routes, three associations)
- `VpcId`, `PrivateSubnetIds` (two subnets in two supported AZs), and `VpcCidr` captured for
  Module 3

## Troubleshooting

**`cdk`/`cfn-lint` not available in the kernel**

The validation cells use `cfn-lint` and the AWS CLI. If `cfn-lint` is not installed, the
notebook reports the validation as skipped rather than failing — the `aws cloudformation
validate-template` check is the authoritative one and needs only the AWS CLI.

**The change-set preview leaves a stack behind**

The notebook's change-set cell creates the change set with `--change-set-type CREATE`
(which never instantiates resources — the placeholder stack sits in `REVIEW_IN_PROGRESS`),
lists it, then deletes both the change set and the placeholder. If a cell errored mid-way,
delete a lingering `atlas-foundation-drycheck` stack from the CloudFormation console.

**You only have a VPC in `us-east-1b`**

That is exactly the case the AZ-exclusion rule guards against. Deploy the foundation into two
supported AZ-IDs (`use1-az1` / `use1-az2` / `use1-az4`) rather than reusing a `us-east-1b`
subnet, or Workshop 2's AgentCore runtimes will later fail to place.

## The honest limit — dry-validated, not live-proven

Be precise about what Module 0 has demonstrated. The template is `cfn-lint`-clean, accepted by
`validate-template`, and a change-set preview confirmed it *would* create exactly the 15
intended resources (then the change set was deleted — no live resources were created). The
outputs were cross-checked against the real consumer inputs. That makes it **config-verified
and contract-matched** — *not* live-proven. A full clean-account run (Module 0 → Workshop 1 →
Workshop 2 from nothing) is a separate exercise, tabled until a genuinely empty account is
available. Treat Module 0 as structurally sound, not as "it works end to end."

## What's Next

With a VPC and two private subnets in supported AZs — and their IDs captured — you have the
foundation the rest of ATLAS assumed into existence. Proceed to
[Module 1 — From Business Question to Ontology](../01-from-business-question/), and pass the
captured outputs to Module 3 when you deploy Neptune.
