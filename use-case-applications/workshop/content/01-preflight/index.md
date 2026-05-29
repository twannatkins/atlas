---
title: "Module 1 — Pre-flight: Is Workshop 1 Ready?"
weight: 10
---

# Module 1 — Pre-flight: Is Workshop 1 Ready?

## Learning Objectives

- Verify that the Workshop 1 substrate (ontology classes, SHACL shapes, the
  synthetic data corpus, and a populated two-tier Neptune) is present and in the
  state Workshop 2 expects
- Confirm Bedrock model access and required Workshop 1 files are in place before
  any build module runs
- Read each pre-flight assertion as a data contract: know exactly what is being
  checked, and what to do if a check fails

## Time Estimate

15–20 minutes. This module builds nothing — it verifies. Budget extra time only if
a check fails and you need to remediate a Workshop 1 gap before continuing.

## Prerequisites

- All steps in [Prerequisites](../00-prerequisites/) complete — in particular,
  `uv sync --all-groups` done and the `atlas-workshop` kernel registered
- The Workshop 1 SLGD reachable and populated (the pre-flight notebook halts at
  the first failed assertion if it is not)

## What You Will Build

Nothing. This notebook runs the data-contract assertions defined in
`spec/03-data-contracts.md` against your Workshop 1 substrate and reports the
first thing that is missing — with a plain-English remediation pointer — rather
than letting a later build module fail confusingly.

The notebook is `notebooks/phase-1-referral/00_preflight.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 2
(`cell-02-concept`) — they explain exactly what Workshop 2 inherits from
Workshop 1 and why a silent failure in the substrate is the hardest kind to
debug.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/00_preflight.ipynb` in SageMaker Studio.
When prompted, select the **ATLAS Workshop 2 (Python 3.12)** kernel registered
during the Prerequisites step.

![Selecting the atlas-workshop kernel](/static/images/01-step-01-kernel-select.png)

### Step 2 — Run setup (cell 5)

Run cell 5 (`cell-05-setup`) to load shared helpers and resolve the repo root.

Expected output (first few lines):

```
Shared helpers loaded from:  .../agentic-semantic-layer/notebooks/shared
Repo root resolved to:       .../atlas
CloudFormation stack name:   atlas-neptune-twotier
AWS region:                  us-east-1
```

### Step 3 — Retrieve Neptune endpoints (cell 6)

Run cell 6 (`cell-06-connect`) to read the SLGD and LGD endpoint addresses
from the Workshop 1 CloudFormation stack outputs.

Expected output:

```
Reading stack outputs from: atlas-neptune-twotier
Stack status:  CREATE_COMPLETE
SLGD endpoint: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
LGD endpoint:  atlas-lgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
NeptuneClient instances ready: slgd, lgd
```

If this cell raises with "Stack not found," the Workshop 1 Neptune stack was not
deployed or was deleted. See the Troubleshooting section below.

### Step 4 — Check 1: Neptune connectivity (cell 7)

Run cell 7 (`cell-07-check1`) to verify both clusters are reachable and the
SLGD has data.

Expected output:

```
Check 1 — Neptune connectivity
--------------------------------------------------
  SLGD total triples: NNN
  LGD total triples:  NNN
  [PASS] Check 1 — both clusters reachable, SLGD populated
```

### Step 5 — Check 2: Ontology classes (cell 8)

Run cell 8 (`cell-08-check2`) to count `atlas:` classes in the SLGD and verify
the 15 classes Workshop 2 agents reference by name are all present.

Expected output (excerpt):

```
Check 2 — Ontology class count and required classes
--------------------------------------------------
  atlas: classes found (22):
    atlas:Account
    atlas:Advisor
    ...
  [PASS] Check 2 — 22 classes found, all 15 required classes present
```

### Step 6 — Check 3: SHACL shapes (cell 9)

Run cell 9 (`cell-09-check3`) to verify all six Workshop 1 SHACL NodeShapes
are loaded in the SLGD.

Expected output:

```
Check 3 — SHACL shapes
--------------------------------------------------
  SHACL NodeShapes found (6):
    atlas:BoundaryShape
    atlas:ComplianceInputShape
    ...
  [PASS] Check 3 — 6 shapes found, all 6 required shapes present
```

### Step 7 — Check 4: Instance data counts (cell 10)

Run cell 10 (`cell-10-check4`) to verify the synthetic corpus matches the
exact counts Workshop 1 produces at random seed 42.

Expected output:

```
Check 4 — Instance data counts
--------------------------------------------------
  [PASS] atlas:Customer                expected   200   found   200
  [PASS] atlas:Transaction             expected  3747   found  3747
  [PASS] atlas:Advisor                 expected    10   found    10
  [PASS] atlas:AdvisoryRelationship    expected   105   found   105
  [PASS] Check 4 — all instance data counts match the data contract
```

### Step 8 — Check 5: Required files (cell 11)

Run cell 11 (`cell-11-check5`) to verify the four Workshop 1 files that
Workshop 2 agents read at runtime are present on disk.

Expected output:

```
Check 5 — Required Workshop 1 file paths
--------------------------------------------------
  [PASS] agentic-semantic-layer/prompts/prefixes.txt
  [PASS] agentic-semantic-layer/prompts/ground-truth.yaml
  [PASS] agentic-semantic-layer/notebooks/shared/atlas_neptune.py
  [PASS] agentic-semantic-layer/notebooks/shared/atlas_sparql.py
  [PASS] Check 5 — all required Workshop 1 files present on disk
```

### Step 9 — Check 6: Bedrock model access (cell 12)

Run cell 12 (`cell-12-check6`) to confirm the two Bedrock models Workshop 2
uses are accessible in your account and region.

Expected output:

```
Check 6 — Bedrock model access
--------------------------------------------------
  [PASS] amazon.titan-embed-text-v2:0
         Used by: nl-to-sparql-agent (embedding-based template selection)
  [PASS] us.anthropic.claude-sonnet-4-6
         Used by: referral-rationale-drafter (narrative drafting)
  [PASS] Check 6 — all required Bedrock models accessible
```

### Step 10 — Pre-flight validation gate (cell 13)

Run cell 13 (`cell-13-gate`) to see the consolidated pass/fail summary across
all six checks.

Expected output:

```
============================================================
PRE-FLIGHT VALIDATION GATE
============================================================
  PASS             Check 1 — Neptune connectivity
  PASS             Check 2 — Ontology classes
  PASS             Check 3 — SHACL shapes
  PASS             Check 4 — Instance data counts
  PASS             Check 5 — Required file paths
  PASS             Check 6 — Bedrock model access

PRE-FLIGHT: PASS
Workshop 1's substrate is confirmed. Workshop 2 is safe to start.
Open notebook 01_why_agents.ipynb to continue.
```

![Pre-flight gate PASS](/static/images/01-step-10-preflight-pass.png)

## Expected Outputs

- All six checks report `[PASS]`
- Pre-flight gate prints `PRE-FLIGHT: PASS`
- No files modified — the notebook is read-only against your environment

## Troubleshooting

**Cell 6 fails with "Stack atlas-neptune-twotier not found"**

The Workshop 1 Neptune stack was either not deployed or was deleted to save cost.
Redeploy from `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml`,
then re-run Workshop 1 modules 3 and 4 to reload the ontology and synthetic data.
Allow approximately 90 minutes. The stack name must match exactly — Workshop 2
reads it by the fixed string `atlas-neptune-twotier`.

**Check 2 fails: missing required classes**

One or more `atlas:` classes are absent from the SLGD. The most common cause is
that the Workshop 1 ontology bulk-load (module 3) completed but the FIBO alignment
file (`atlas-fibo-alignment.ttl`) was not included in the S3 staging upload. Re-run
Workshop 1 module 3, confirming all four ontology files are uploaded before
triggering the bulk load.

**Check 4 fails: instance data counts wrong**

The synthetic data counts do not match the data contract. If the module 4
data-loading cells were interrupted, some batches may not have written to Neptune.
Re-run Workshop 1 module 4 from the top. If you regenerated synthetic data with a
different random seed, you must use the original `seed=42` or the exact counts
will not match.

**Check 6 fails: Bedrock model not accessible**

`us.anthropic.claude-sonnet-4-6` requires using the US cross-region inference
profile — the bare foundation model ID will not work. If the model ID appears
correct but the check still fails, verify that the SageMaker execution role has
`bedrock:InvokeModel` and `bedrock:ListFoundationModels` permissions, and that you
are running in `us-east-1`. Non-US regions must override `BEDROCK_TEXT_MODEL_ID`
to `global.anthropic.claude-sonnet-4-6`.

## What's Next

The substrate is confirmed. [Module 2 — Why Agents at All?](../02-why-agents/)
introduces the architectural pattern that every Phase 1 agent implements: Bedrock
at the edges for language translation, deterministic reasoning in the middle. That
boundary is what makes ATLAS auditable under SR 11-7, and it is the most important
idea in Workshop 2.
