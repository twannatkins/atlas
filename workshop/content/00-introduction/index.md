---
title: "Introduction"
weight: 0
---

# ATLAS — Aligned Three-Layer Architecture for Semantics

Welcome to the ATLAS workshop. Over the next 5–6 hours, you will build a complete
enterprise semantic layer for Financial Services on AWS — from a blank competency
question to a running wealth-signal detection demo with full audit trail.

## What You Will Build

By the end of this workshop, you will have:

- A **FIBO-aligned ontology** with 19 classes derived from competency questions
- **Two Amazon Neptune clusters** (LGD and SLGD) running a two-tier graph architecture
- **Three data integration patterns** feeding source data into the graph
- **SHACL shapes** that mechanically enforce the deterministic-vs-probabilistic boundary
- A **natural-language-to-SPARQL** component powered by Amazon Bedrock
- An **end-to-end wealth-signal workflow** from signal detection through advisor approval
- A **one-query audit trail** you can demo to a CIO in 30 seconds

## Who This Workshop Is For

- **FSI architects** who need to build and defend a knowledge graph to a Model Risk
  Management (MRM) reviewer
- **Data engineers** who want to understand how ontologies connect to real data pipelines
- **Ontologists** who want to see FIBO alignment applied to a concrete use case on AWS

**No prior ontology experience is required.** Module 1 teaches ontology concepts
from scratch using a Socratic method with Amazon Bedrock.

## The Architecture

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

## The Central Commitment

Every component in ATLAS is classified as one of:

- **DETERMINISTIC** — same inputs always produce the same outputs (SHACL validation,
  route selection, SPARQL queries, R2RML mappings)
- **PROBABILISTIC-EXPLAINABLE** — non-deterministic but produces per-record explanations
  (XGBoost scoring with SHAP attributions)
- **PROBABILISTIC-OPAQUE** — non-deterministic without per-record explanations
  (Bedrock narrative drafting — interface role only, never a decision input)

The boundary between these classes is enforced mechanically by SHACL shapes. A
reviewer can run one validator and produce a report.

## Module Overview

| # | Module | What You Learn | Time |
|---|--------|----------------|------|
| 1 | From Business Question to Ontology | Derive an ontology from competency questions | 30–45 min |
| 2 | FIBO Alignment and the Extension Ring | Bind your ontology to the industry standard | 60–75 min |
| 3 | Standing Up Two-Tier Neptune | Deploy graph infrastructure on AWS | 20–30 min |
| 4 | Three Patterns for Source Connection | Connect source systems to a knowledge graph | 60–75 min |
| 5 | Entity Resolution and the Promotion Path | Resolve identities and govern data promotion | 30–45 min |
| 6 | SHACL: Making the Boundary Mechanical | Enforce rules with machine-checkable shapes | 45–60 min |
| 7 | Bedrock at the Edges | Use LLMs safely in a regulated architecture | 30–45 min |
| 8 | The Wealth-Signal Demo with Bounded Agent | End-to-end workflow from signal to approval | 45–60 min |

## How to Use This Workshop

Each module follows the same pattern:

1. **Read** the learning objectives and key concepts
2. **Open** the corresponding Jupyter notebook in SageMaker
3. **Run** cells sequentially, reading the educational prose between code cells
4. **Pass** the validation gate at the end of each module before proceeding

Modules must be completed in order — each builds on the deliverables of the previous one.

## Let's Begin

Proceed to [Prerequisites](../00-prerequisites/) to set up your AWS environment,
then start with [Module 1](../01-from-business-question/).
