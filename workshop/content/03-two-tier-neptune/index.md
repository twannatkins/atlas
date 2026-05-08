---
title: "Module 3 — Standing Up Two-Tier Neptune"
weight: 30
---

# Module 3 — Standing Up Two-Tier Neptune

## Learning Objectives

- Deploy two Amazon Neptune serverless clusters (LGD and SLGD) via CloudFormation
  and explain the architectural reason for the two-tier split
- Load a FIBO-aligned ontology into the SLGD using Neptune's bulk loader from S3
- Run SPARQL discovery queries against a live Neptune cluster and interpret the results
- Verify that the LGD is empty and accessible from the SLGD, confirming the
  two-tier topology is operational

## Time Estimate

20 to 30 minutes (plus 5–10 minutes for Neptune cluster provisioning).

## Prerequisites

- Module 2 complete (`ontology/atlas-fibo-alignment.ttl` and `ontology/alignment-gaps.md`)
- AWS account with permissions to create Neptune clusters, IAM roles, S3 buckets,
  and security groups
- A VPC with at least two subnets in different Availability Zones

## What You Will Build

This module deploys the physical graph infrastructure that every subsequent module
builds against:

- Two Neptune serverless clusters: `atlas-lgd` (raw, unvalidated) and `atlas-slgd`
  (curated, FIBO-aligned)
- The SLGD loaded with the ontology from Modules 1 and 2
- An S3 staging bucket for ontology file loading
- A CloudFormation template at `infrastructure/atlas-neptune-twotier.yaml`

The notebook is `notebooks/03_two_tier_neptune.ipynb`.

## Steps

### Step 1 — Deploy the CloudFormation stack

If you have not already deployed the Neptune stack, run the following in a terminal
(replacing the VPC and subnet IDs with your own):

```bash
aws cloudformation create-stack \
  --stack-name atlas-neptune-twotier \
  --template-body file://infrastructure/atlas-neptune-twotier.yaml \
  --parameters \
    ParameterKey=VpcId,ParameterValue=vpc-XXXXXXXXX \
    ParameterKey=SubnetIds,ParameterValue=subnet-AAA\\,subnet-BBB\\,subnet-CCC \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

Neptune serverless clusters take approximately 5–10 minutes to provision.

![CloudFormation stack creating](/static/images/03-step-01-cfn-creating.png)

### Step 2 — Open the notebook and retrieve endpoints

Open `notebooks/03_two_tier_neptune.ipynb`. Run cell 3 to wait for the stack to
complete and retrieve the Neptune endpoints.

Run cell 3. Expected output:

```
Stack status: CREATE_COMPLETE

LGD  endpoint: atlas-lgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
SLGD endpoint: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
S3 bucket:     atlas-ontology-staging-XXXXXXXXXXXX
Neptune role:  arn:aws:iam::XXXXXXXXXXXX:role/atlas-neptune-s3-access
```

### Step 3 — Upload ontology files to S3

Run cell 5 to upload the four ontology files to the S3 staging bucket.

Run cell 5. Expected output:

```
Uploading ontology files to s3://atlas-ontology-staging-XXXXXXXXXXXX/ontology/

  [OK] ontology/atlas-core.ttl -> s3://.../ontology/atlas-core.ttl
  [OK] ontology/atlas-fibo-alignment.ttl -> s3://.../ontology/atlas-fibo-alignment.ttl
  [OK] ontology/extensions/skos-codelists.ttl -> s3://.../ontology/skos-codelists.ttl
  [OK] ontology/extensions/gleif-bindings.ttl -> s3://.../ontology/gleif-bindings.ttl

Upload complete.
```

### Step 4 — Bulk load ontology into the SLGD

Run cell 7 to trigger Neptune's bulk loader. This loads all four Turtle files into
the SLGD in a single operation.

![Bulk load complete](/static/images/03-step-04-bulkload-complete.png)

Run cell 7. Expected output:

```
Triggering bulk load into SLGD...
  Source: s3://atlas-ontology-staging-XXXXXXXXXXXX/ontology/
  Target: https://atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182

Load initiated. Load ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
  Status: LOAD_IN_PROGRESS
  Status: LOAD_COMPLETED

Bulk load complete.
```

### Step 5 — Run SPARQL discovery queries

Run cell 9 to execute the four discovery queries against the SLGD.

![SPARQL discovery results](/static/images/03-step-05-sparql-discovery.png)

Run cell 9. Expected output (excerpt):

```
Query 1: All OWL classes in the SLGD
------------------------------------------------------------
Classes found: 21
  Account                        Account
  Advisor                        Advisor
  ...

Query 2: Classes with direct subclasses
------------------------------------------------------------
  IndependentParty                 1 subclass(es)
  FinancialAccount                 2 subclass(es)
  ...

Query 3: Object properties with domain/range
------------------------------------------------------------
Object properties found: 18
  conductedBy               HumanReview          -> Advisor
  evidencedBy               WealthSignal         -> Transaction
  ...
```

### Step 6 — Verify LGD is empty

Run cell 10 to confirm the LGD has zero triples and the SLGD has the ontology loaded.

Run cell 10. Expected output:

```
Query 4: LGD triple count (should be 0)
------------------------------------------------------------
LGD triples: 0
[PASS] LGD is empty as expected.

SLGD triples: 353
[PASS] SLGD has ontology data loaded.
```

### Step 7 — Run the validation gate

Run cell 12 (the Module 3 validation gate). All four sub-gates must pass.

![Module 3 validation gate PASS](/static/images/03-step-07-validation-pass.png)

Run cell 12. Expected output:

```
============================================================
MODULE 3 VALIDATION GATE
============================================================
[PASS] Gate 1 — SLGD has 21 atlas: classes (expected >= 18)
[PASS] Gate 2 — LGD is empty (0 triples)
[PASS] Gate 3 — SLGD queryable (353 total triples)
[PASS] Gate 4 — atlas-lgd status: available
[PASS] Gate 4 — atlas-slgd status: available

MODULE 3 VALIDATION: PASS
You may proceed to Module 4.
```

## Expected Outputs

After completing this module:

- CloudFormation stack `atlas-neptune-twotier` in `CREATE_COMPLETE` status
- Neptune cluster `atlas-lgd` — available, zero triples
- Neptune cluster `atlas-slgd` — available, ontology loaded (~353 triples)
- S3 bucket with ontology files staged
- Module 3 validation gate prints `MODULE 3 VALIDATION: PASS`

## Troubleshooting

**Stack creation fails with "Subnet group must contain at least 2 subnets in different AZs"**

Neptune requires subnets in at least two different Availability Zones. Check that
your `SubnetIds` parameter includes subnets from different AZs. Use
`aws ec2 describe-subnets` to verify the AZ of each subnet.

**Bulk load fails with "Access Denied" from S3**

The Neptune IAM role (`atlas-neptune-s3-access`) must have read access to the S3
bucket AND the role must be associated with the Neptune cluster. The CloudFormation
template handles both, but if you deployed manually, verify with
`aws neptune describe-db-clusters` that the role ARN appears in `AssociatedRoles`.

**SPARQL queries time out or connection refused**

Neptune is only accessible from within the VPC. If you are running the notebook
from outside the VPC (e.g., a local machine), the connection will fail. Run the
notebook from a SageMaker instance in the same VPC, or set up a VPC endpoint.

**Stack creation fails with "Role atlas-neptune-s3-access already exists"**

A previous deployment left the IAM role behind. Delete it manually with
`aws iam delete-role --role-name atlas-neptune-s3-access` (after detaching any
policies), then retry the stack creation.

## Extending This to Your Data

The appendix in the notebook (cell 13) covers: sizing the two clusters for
production loads, when to add read replicas, the most common networking gotcha
(SPARQL SERVICE between clusters requires same-VPC or VPC peering with explicit
routes), and how to bind the workshop's IAM roles into your existing role-based
access pattern.

## What's Next

Module 3 deployed the graph infrastructure. The SLGD has the ontology; the LGD is
empty. Module 4 answers: how do we get data into the LGD from three different source
patterns (Iceberg, Snowflake Horizon, and a real-time stream)? The answer involves
R2RML mappings, Ontop virtual knowledge graph projection, and a Lambda consumer —
all feeding the LGD with raw triples that Module 5 will later promote to the SLGD.
