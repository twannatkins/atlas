---
title: "Welcome to ATLAS"
weight: 1
---

# Welcome

Over the next day, you are going to build an **ontology**.

Not a vocabulary written in a document. Not a class diagram in a slide deck. A working, queryable, federated, governed ontology, hosted on Amazon Neptune, aligned to the Financial Industry Business Ontology (FIBO), and ready for AI agents to operate against.

By the end of this workshop, you will have built a *semantic layer for agentic AI*: the substrate that lets enterprise AI agents query your bank's data, reason about it within model risk policy, and produce auditable answers without hallucinating.

Workshop 2 (`use-case-applications/`) takes this substrate and builds two real banking applications on top of it — a Wholesale UI for Consumer Banker referrals, a Wealth UI for the advisor workbench, both backed by registered agents and a FIBO-shaped GraphQL API. But none of that works without what you build today.

## Why we start here

Enterprise AI agents in regulated industries have a structural problem. Language models hallucinate. They invent account numbers, fabricate relationships, mis-classify customers. In a consumer chatbot this is annoying. In a wealth referral, a compliance review, or a risk decision, it is unacceptable — and it is a violation of model risk regulations that exist for exactly this reason (SR 11-7, OCC 2011-12).

The way around this is not to make the model better. The way around this is to *ground* the model in a layer that has explicit semantics, deterministic validation, and full provenance. An ontology.

That is what you build today. The agents in Workshop 2 don't hallucinate — not because they're better agents, but because they operate against a graph that won't let them. Every triple in the graph is validated by a SHACL shape. Every probabilistic output carries a flag. Every compliance decision carries an explainability artifact. The agents inherit all of this automatically because they query a substrate that already enforces it.

This is the architectural decision that makes ATLAS different from a generic agentic AI platform. You will learn it by building it.

## What the day looks like

Eight modules, roughly 45–60 minutes each, with breaks. Each module is a Jupyter notebook. Each notebook has the same shape: a question you would naturally ask, the concept that answers it, the artifact that embodies the concept, and the next question that the artifact opens.

| # | Module | The question it answers |
|---|---|---|
| 1 | Journey to ontology | Why an ontology — and not a CRM or a data warehouse — is the right substrate for agentic AI |
| 2 | FIBO alignment | What FIBO is, why it matters, how to extend it where it doesn't cover what your bank uses |
| 3 | Two-tier Neptune | Why the graph has two tiers (LGD for raw facts, SLGD for the curated ontology) and what each one is for |
| 4 | Three connection patterns | How enterprise data flows into the ontology — Iceberg, Snowflake Horizon, real-time events — without bulk migration |
| 5 | Entity resolution | How AWS Entity Resolution mints canonical URIs, and what to do when records don't match |
| 6 | The SHACL boundary | The most important hour of the day. Where the deterministic boundary lives, why SHACL draws it, and why this is the SR 11-7 story |
| 7 | Bedrock at the edges | Why Bedrock is at the *edges* of the architecture — translating natural language to SPARQL — not in the *middle* reasoning over data |
| 8 | Wealth signal demo | A worked example: surfacing a wealth-eligible customer through SHACL shapes and SPARQL CONSTRUCT queries, end to end |

By module 8 you will see, end to end, how a customer event flows from a source system into the graph, through a shape that validates it, through a SPARQL CONSTRUCT that derives a signal from it, and out to an answer that a banker could trust. Every step will be inspectable. Every step will be auditable. Every step will be yours.

## What you'll have at the end

A FIBO-aligned ontology of 24 classes (19 core domain + 3 FIBO alignment + 2 governance) covering customers, accounts, holdings, transactions, advisors, households, signals, and the governance scaffolding around all of it. Six SHACL shapes that draw the deterministic boundary. Three R2RML mappings that federate enterprise data sources without copying their bytes. A two-tier Neptune deployment populated with 200 synthetic customers, 3,747 transactions, 10 advisors, and 105 advisory relationships. Bedrock at the edges, translating natural language to SPARQL through a ground-truth set of question-answer pairs.

You will have this in a working AWS environment. You will be able to query it. You will be able to extend it. And tomorrow, when you move to Workshop 2, you will be able to point agents at it.

## How to read the notebooks

Each notebook follows a five-section pattern: the question, the concept, the build, the verification, what just changed. Read the concept sections carefully — they are where the teaching lives. The build cells produce the artifacts; the concept sections explain why the artifacts exist.

If you find yourself executing cells without absorbing the *why*, slow down. This workshop is dense. The reading is the teaching.

## What you need before you start

See `00-prerequisites/index.md` for the complete prerequisite list. Briefly: an AWS account with permissions to deploy Neptune, Bedrock model access, SageMaker Studio domain access, and comfort with Jupyter notebooks. You do not need local Python, local Docker, or local AWS CLI. Everything runs in Studio.

When you're ready, open `01-from-business-question/index.md` and begin.
