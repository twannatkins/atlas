---
title: "Module 4 — Three Patterns for Source Connection"
weight: 40
---

# Module 4 — Three Patterns for Source Connection

## Learning Objectives

- Explain what a Virtual Knowledge Graph (VKG) is and why it avoids copying
  petabytes of warehouse data into a graph database
- Read and write R2RML (Relational-to-RDF Mapping Language) mappings that project
  relational rows as RDF triples
- Federate three source systems into the LGD using three different integration
  patterns (Iceberg, Snowflake Horizon, real-time stream)
- Consume a real-time event stream via AWS Lambda and write triples to Neptune
- Verify that the LGD contains data from all three sources via a cross-source
  SPARQL query

## Time Estimate

60 to 75 minutes.

## Prerequisites

- Module 3 complete (both Neptune clusters running, SLGD loaded with ontology)
- CloudFormation stack `atlas-neptune-twotier` in `CREATE_COMPLETE` status
- Optional: a Snowflake account for the Horizon path (Athena fallback provided)

## What You Will Build

This module populates the LGD (Lexical Graph Database) with data from three source systems:

- **Pattern A**: Customer master data (200 records) via S3 Iceberg and R2RML
  (Relational-to-RDF Mapping Language)
- **Pattern B**: Transaction history (~3,750 records) via Athena and R2RML
- **Pattern C**: Real-time wealth-eligibility events via Lambda

The notebook is `notebooks/04_three_connection_patterns.ipynb`.
Supporting files: `mappings/` (R2RML and Lambda code), `data/synthetic/` (source data).

## How This Connects to Competency Questions

Competency Questions (CQs) can only be answered if the graph has data. Module 4
is where data arrives. Each connection pattern feeds specific CQs:

- **Pattern A** (customer master) feeds CQ1, CQ3, CQ4 — questions about customers,
  households, and prior surfacing
- **Pattern B** (transactions) feeds CQ1, CQ2, CQ7 — questions about signals,
  evidence, and specific observations
- **Pattern C** (real-time events) feeds CQ1, CQ5 — questions about signal
  detection and workflow triggering

If a CQ can't be answered after this module, it means one of the patterns didn't
load the right data. The validation gate at the end checks cross-source query
results — which is really checking that the data needed for CQs is present.

## Steps

Before running any code, read cell 1 of the notebook — it contains the module
introduction and a Key Terms table. The vocabulary defined there is referenced
throughout the rest of the module.

### Step 1 — Open the notebook and retrieve Neptune endpoints

Open `notebooks/04_three_connection_patterns.ipynb`. Run cell 2 (setup) to load
shared utilities and retrieve the Neptune endpoints from the Module 3 stack.
The Neptune client authenticates using SigV4 signing — your SageMaker execution
role's credentials are used automatically, so no connection strings or passwords
are needed.

Run cell 2. Expected output:

```
ATLAS shared utilities loaded.
Synthetic data seed: 42

Neptune LGD:  atlas-lgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
Neptune SLGD: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
```

### Step 2 — Read the Pattern A explanation and run the data generation

Read cell 3 (Pattern A explanation). Then run cell 4 to generate and upload
the customer master data to S3.

![Pattern A data upload](/static/images/04-step-02-pattern-a-upload.png)

Run cell 4. Expected output:

```
Customer master: 200 records
Columns: ['customer_id', 'first_name', 'last_name', 'state', 'segment', ...]
Uploaded to s3://atlas-ontology-staging-XXXXXXXXXXXX/data/iceberg/...
```

### Step 3 — Read the Pattern B explanation and generate transactions

Read cell 5 (Pattern B explanation). Run cell 6 to generate transaction history.

Run cell 6. Expected output:

```
Transaction history: 3747 records
Embedded wealth-signal transactions:
  large-deposit-pattern: 12
  equity-event-signal: 7
  retirement-rollover-signal: 5
  business-sale-liquidity-signal: 3
```

### Step 4 — Read the Pattern C explanation and see the event mapping

Read cell 7 (Pattern C explanation). Run cell 8 to see how one event is
converted to RDF triples. Note how the Lambda uses the system trust store for
TLS verification when connecting to Neptune — the Amazon RDS CA certificates
are available in the Lambda runtime environment, so the connection is encrypted
and authenticated without any custom certificate management.

![Pattern C event mapping](/static/images/04-step-04-pattern-c-mapping.png)

Run cell 8. Expected output shows one event converted to N-Triples format.

### Step 5 — Write all patterns to the LGD

Run cell 10 to write triples from all three patterns to the LGD.

Run cell 10. Expected output:

```
Writing Pattern A (Customer Master) to LGD...
  Pattern A: 600 triples written

Writing Pattern B (Transaction History) to LGD...
  Pattern B: 2000 triples written

Writing Pattern C (Event Stream) to LGD...
  Pattern C: ~155 triples written

Total triples written to LGD: ~2755
```

### Step 6 — Run the validation gate

Run cell 12 (Module 4 validation gate). All five sub-gates must pass.

![Module 4 validation gate PASS](/static/images/04-step-06-validation-pass.png)

Run cell 12. Expected output:

```
============================================================
MODULE 4 VALIDATION GATE
============================================================

[PASS] Gate 1 - Pattern A: 200 Customer nodes in LGD
[PASS] Gate 2 - Pattern B: 500 Transaction nodes in LGD
[PASS] Gate 3 - Pattern C: 31 BehavioralEvent nodes in LGD
[PASS] Gate 4 - Cross-source: 200 customers with household links
[PASS] Gate 5 - LGD total: ~2755 triples

MODULE 4 VALIDATION: PASS
You may proceed to Module 5.
```

## Expected Outputs

After completing this module:

- LGD populated with triples from all three source patterns
- Customer nodes (Pattern A), Transaction nodes (Pattern B), and
  BehavioralEvent nodes (Pattern C) all queryable via SPARQL
- Cross-source SPARQL query returns results spanning multiple patterns
- Module 4 validation gate prints `MODULE 4 VALIDATION: PASS`

## Troubleshooting

**Cell 10 fails with "Connection refused" or timeout**

Neptune is only accessible from within the VPC. Ensure you are running the
notebook from a SageMaker instance in the same VPC as the Neptune clusters.
Check the security group allows port 8182 traffic.

**Cell 10 fails with "SSL: CERTIFICATE_VERIFY_FAILED"**

The Lambda connects to Neptune over HTTPS using the system trust store, which
includes the Amazon RDS root CA. If you see certificate errors, ensure your
Lambda runtime is up to date (Python 3.10+) and that the Neptune cluster
endpoint matches the certificate's Common Name. Do not disable certificate
verification — the Amazon RDS CA is trusted by default in all current Lambda
runtimes.

**Cell 12 Gate 1 fails with "0 Customer nodes"**

The Pattern A write in cell 10 did not complete. Check for errors in cell 10
output. Most common cause: the Neptune endpoint variable is empty (Module 3
stack not deployed or outputs not retrieved).

**Cell 6 shows different signal counts than expected**

The synthetic data generator uses a fixed seed (42). If you modified
`atlas_synthetic.py` or changed the seed, counts will differ. Reset to the
original file from the repository.

**Parquet conversion fails with "No module named pyarrow"**

pyarrow is pinned in `notebooks/shared/requirements.txt` (version 14.0.2). If
you see this error, your environment didn't install requirements correctly.
Re-run the prerequisites step `pip install -r notebooks/shared/requirements.txt`
from a kernel restart to refresh the environment.

## Extending This to Your Data

The notebook appendix (cell 13) covers: writing R2RML mappings for the three
most common production patterns (snake_case to camelCase, composite keys,
optional foreign keys), the Snowflake external-volume bucket-name gotcha
(no dots in bucket names), and the most common Ontop deployment misstep
(under-sized Fargate memory for large R2RML files).

## What's Next

Module 4 filled the LGD with raw data from three sources. But the same
customer may appear in Pattern A (customer master) and Pattern B (transactions)
with different identifiers. Module 5 asks: which of these records refer to the
same real-world entity? AWS Entity Resolution resolves cross-source identities,
and the promotion path moves validated data from the LGD to the SLGD with full
provenance attribution.
