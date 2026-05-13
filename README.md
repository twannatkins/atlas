# ATLAS — Aligned Three-Layer Architecture for Semantics

An open-source Financial Services Industry (FSI) semantic layer reference architecture
and Amazon SageMaker notebook workshop on AWS.

**Lead use case:** Identifying wealth signals from inside the bank.
**Audience:** FSI architects and ontologists who need to build and defend a
knowledge graph to a Model Risk Management (MRM) reviewer.

---

## What ATLAS Is

ATLAS demonstrates how to build an AWS-native enterprise semantic layer for FSI
institutions. It implements a three-layer pattern — data integration, ontology
and digital twin, and application — bound to the Financial Industry Business
Ontology (FIBO) as its alignment vocabulary.

The architecture's central commitment is the **deterministic-vs-probabilistic
boundary**: every component is classified, the boundary is enforced by Shapes
Constraint Language (SHACL) shapes, and the shapes are runnable artifacts in
this repository. A Model Risk Management reviewer can run one validator and
produce a report showing exactly where probabilistic outputs entered the system
and exactly which deterministic constraints prevent them from corrupting
compliance-bound paths.

ATLAS is not a productized platform. It is a reference pattern with runnable code.

---

## Architecture in 30 Seconds

```
┌─────────────────────────────────────────────────────────────────┐
│  Application Layer                                              │
│  Bedrock (NL↔SPARQL only) · Step Functions agent · AppSync UI  │
├─────────────────────────────────────────────────────────────────┤
│  Ontology and Digital Twin Layer                                │
│  LGD (raw, unvalidated)  →  SLGD (FIBO-aligned, SHACL-valid)  │
│  Amazon Neptune two-tier · SHACL boundary enforcement           │
├─────────────────────────────────────────────────────────────────┤
│  Data Integration Layer                                         │
│  Pattern A: S3 Iceberg → Ontop → R2RML                          │
│  Pattern B: Snowflake Horizon (or Athena fallback) → Ontop      │
│  Pattern C: Kinesis/MSK → Lambda → LGD                          │
└─────────────────────────────────────────────────────────────────┘
```

LGD = Lexical Graph Database (fast, lossy, not authoritative).
SLGD = Semantic Layer Graph Database (curated, validated, authoritative).

---

## Eight-Module Table of Contents

| # | Module | What You Learn | Runtime |
|---|--------|----------------|---------|
| 1 | [From Business Question to Ontology](notebooks/01_journey_to_ontology.ipynb) | How to derive an ontology from competency questions | 30–45 min |
| 2 | [FIBO Alignment and the Extension Ring](notebooks/02_fibo_alignment.ipynb) | How to bind your ontology to the industry standard (FIBO) | 60–75 min |
| 3 | [Standing Up Two-Tier Neptune](notebooks/03_two_tier_neptune.ipynb) | How to deploy graph infrastructure on AWS | 20–30 min |
| 4 | [Three Patterns for Source Connection](notebooks/04_three_connection_patterns.ipynb) | How to connect source systems to a knowledge graph | 60–75 min |
| 5 | [Entity Resolution and the Promotion Path](notebooks/05_entity_resolution.ipynb) | How to resolve identities and govern data promotion | 30–45 min |
| 6 | [SHACL: Making the Boundary Mechanical](notebooks/06_shacl_boundary.ipynb) | How to enforce rules with machine-checkable shapes | 45–60 min |
| 7 | [Bedrock at the Edges](notebooks/07_bedrock_at_edges.ipynb) | How to use LLMs safely in a regulated architecture | 30–45 min |
| 8 | [The Wealth-Signal Demo with Bounded Agent](notebooks/08_wealth_signal_demo.ipynb) | End-to-end workflow from signal to advisor approval | 45–60 min |

Total: approximately 5–6 hours of focused work.

---

## Prerequisites

### Required Knowledge

- **No prior ontology experience required.** Module 1 teaches ontology concepts from scratch.
- Basic Python familiarity (reading code, running notebooks)
- Basic AWS console navigation (creating stacks, finding services)

### AWS Account Requirements

You need an AWS account with the following services enabled in **us-east-1**:

| Service | Used In | Purpose |
|---------|---------|---------|
| Amazon SageMaker | All modules | Notebook execution environment |
| Amazon Neptune | Modules 3–8 | Graph database (two serverless clusters) |
| Amazon Bedrock | Modules 1, 7, 8 | LLM for ontology exploration and NL↔SPARQL |
| Amazon S3 | Modules 3–4 | Ontology staging and data lake |
| AWS CloudFormation | Module 3 | Infrastructure deployment |
| Amazon Athena | Module 4 | SQL queries over S3 data |
| AWS Glue | Module 4 | Data catalog for Iceberg tables |

### Setup Checklist

Before starting Module 1, complete these steps (detailed walkthrough in
[workshop/content/00-prerequisites/](workshop/content/00-prerequisites/index.md)):

1. **Open SageMaker Studio** in us-east-1 and create a JupyterLab space
   - Instance type: `ml.t3.medium` is sufficient
   - Image: SageMaker Distribution 2.x (includes Python 3.10+)

2. **Clone this repository** in the JupyterLab terminal:
   ```bash
   git clone https://github.com/twannatkins/atlas.git
   cd atlas
   pip install -r notebooks/shared/requirements.txt
   ```

3. **Enable Amazon Bedrock model access**
   - Open the Bedrock console in us-east-1
   - Go to Model access → Manage model access
   - Enable access to **Anthropic Claude Sonnet**
   - This takes 1–2 minutes to activate

4. **Add IAM permissions** to your SageMaker execution role
   - S3, Neptune, Athena, Glue, CloudFormation (managed policies)
   - Bedrock InvokeModel (inline policy)

5. **Note your VPC and subnet IDs** (needed for Module 3)
   - Record your VPC ID, CIDR block, and at least two subnet IDs in different AZs
   - Must be the same VPC as your SageMaker Studio domain

### IAM Permissions

The SageMaker execution role needs these managed policies:

- `AmazonSageMakerFullAccess` (notebook execution)
- `AmazonS3FullAccess` (data staging)
- `NeptuneFullAccess` (graph database access)
- `AmazonAthenaFullAccess` (SQL queries in Module 4)
- `AWSGlueServiceRole` (data catalog in Module 4)
- `AWSCloudFormationFullAccess` (stack deployment in Module 3)

Plus this inline policy for Bedrock:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": "arn:aws:bedrock:*::foundation-model/*"
  }]
}
```

### Python Version

This workshop requires **Python 3.10 or later**. Python 3.9 reached end-of-life
in October 2025. SageMaker Studio and SageMaker notebook instances ship with
Python 3.10+ by default.

---

## Cost to Run

A single architect completing the full workshop end-to-end (approximately five to
six hours of active infrastructure time) should expect **$10–$18 in us-east-1**:

| Resource | Approximate Cost | Notes |
|----------|-----------------|-------|
| Neptune serverless (2 clusters) | ~$8.50/day | Scales to zero when idle; ~$17/day at minimum capacity |
| SageMaker notebook | ~$0.05/hr | ml.t3.medium |
| Bedrock invocations | ~$1–3 total | Modules 1, 7, 8 |
| S3 + Athena | < $0.50 | Minimal data volume |

**Important:** Run the cleanup at the end of your session. The two Neptune clusters
cost approximately $17 per day combined if left running.

---

## Workshop Guide

The step-by-step guide lives in [workshop/content/](workshop/content/) and renders
as an AWS Workshop Studio site. Begin with Module 1 at
[workshop/content/01-from-business-question/index.md](workshop/content/01-from-business-question/index.md).

---

## Key Concepts for Newcomers

If you are new to ontologies and knowledge graphs, here are the core concepts
you will learn in this workshop:

| Concept | What It Is | Where You Learn It |
|---------|-----------|-------------------|
| **Ontology** | A formal vocabulary that defines the nouns (classes) and verbs (properties) in your domain | Module 1 |
| **FIBO** | The Financial Industry Business Ontology — a shared vocabulary for FSI | Module 2 |
| **RDF / Triples** | The data format for knowledge graphs: subject → predicate → object | Module 1 |
| **SPARQL** | The query language for RDF graphs (like SQL for relational databases) | Modules 1, 7 |
| **Neptune** | AWS's managed graph database service | Module 3 |
| **SHACL** | Shapes Constraint Language — machine-checkable rules for your graph | Module 6 |
| **R2RML** | A W3C standard for mapping relational data to RDF triples | Module 4 |
| **PROV-O** | W3C Provenance Ontology — records who did what, when, from what | Module 5 |

---

## Synthetic Data

All data in this workshop is synthetic, generated with a fixed random seed (42).
No real customer data is used anywhere. Generators are in
[notebooks/shared/atlas_synthetic.py](notebooks/shared/atlas_synthetic.py).

The synthetic dataset includes:
- 200 customers across 3 segments (Retail, Mass Affluent, Affluent)
- ~3,750 transactions with 27 embedded wealth-signal patterns
- 10 advisor personas (including "Alex Morgan" — the demo reviewer)
- 105 legacy advisory coverage relationships

---

## Mapping This to Your Industry

The wealth-signal use case is the vehicle; the architecture is the product.
Architectural commentary in every module is industry-neutral.

- **Insurance:** replace wealth-signal taxonomy with claim-pattern-to-product-fit signals
- **Asset management:** replace with family-office relationship surface signals
- **Capital markets:** replace with counterparty-to-product fit signals

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Bedrock model not available" | Enable model access in the Bedrock console (us-east-1) |
| "Neptune not reachable" | Ensure your SageMaker instance is in the same VPC as Neptune |
| CloudFormation stack fails | Check that your VPC has at least 2 subnets in different AZs |
| `ModuleNotFoundError: rdflib` | Run `pip install -r notebooks/shared/requirements.txt` |
| Neptune clusters cost too much | Delete the CloudFormation stack when not actively working |

---

## License

MIT-0. See [LICENSE](LICENSE).

FIBO is published under the MIT license by the Enterprise Data Management Council (EDM Council).
The version of FIBO pinned in this workshop is cited in [ontology/README.md](ontology/README.md).

---

## Contributing

Contribution guidelines and security policy will be added before the public release.
