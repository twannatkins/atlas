---
title: "Introduction"
weight: 0
---

# Introduction

You have built a semantic layer. Now you are going to put applications on top of it.

Workshop 1 produced a FIBO-aligned ontology, six SHACL shapes, three R2RML mappings, and a two-tier Neptune deployment populated with synthetic customers, transactions, advisors, and households. Workshop 2 takes that substrate and builds two real banking applications on top of it — without modifying a single file that Workshop 1 produced.

The two applications are:

- **The Wholesale UI** — a Consumer Banker's workbench for identifying wealth-referral candidates and routing them to the advisory team, backed by AI agents that surface wealth signals from the semantic graph
- **The Wealth UI** — an advisor's workbench for managing their referral pipeline, preparing for client conversations, and tracking market themes, backed by a different set of agents with persistent conversational memory

Both applications are governed by the same permission model. The layers enforced today are Identity (IAM Identity Center), Application (Cognito persona claim), field/capability access (AppSync authorization by Cognito group plus per-agent allow-lists — the persona is validated for *which fields and actions it may invoke*), and Semantic (SHACL on writes and decisions). A further layer — per-row Lake Formation data scoping, where the same query returns different rows per persona — is on the roadmap but not yet enforced. Both applications consume the same FIBO-shaped GraphQL API. Both drive their capability palettes from a live Agent Registry query rather than hardcoded feature flags.

## Why this architecture looks the way it does

The agents in ATLAS do not reason. They translate. A banker doesn't speak SPARQL — they speak business questions. An agent's job is to translate a business question into a graph operation, execute it against the ontology, and return the result. The agent is an interface, not a reasoner.

This is the architectural constraint that SR 11-7 and OCC 2011-12 impose on model risk management: if an AI system makes a decision, that decision must be deterministic and explainable. A language model reasoning over customer data is neither. A language model translating natural language to a pre-approved SPARQL query, executing it against a SHACL-validated graph, and returning the results is both. Workshop 2 builds the former kind of system by design, not by accident.

Every agent in ATLAS enforces this at the code level: Bedrock is called only for natural-language translation and narrative drafting. The routing logic, signal detection, entity resolution, and validation all run deterministically against the graph.

## What the two phases cover

Workshop 2 is divided into two phases.

**Phase 1 — Consumer-to-Wealth Referral** covers the Wholesale UI use case end to end. Seven modules, roughly a full working day. You deploy MCP servers, register agents, wire a FIBO-shaped GraphQL API, and deploy the Wholesale UI. The Rachel Kim scenario — Dana Brooks, a Consumer Banker, identifies the customer Rachel Kim's household by its wealth signal and routes it to a Wealth Advisor — is the acceptance test for Phase 1.

**Phase 2 — Wealth Advisor Spine** adds the Wealth UI, AgentCore Memory, JWT-based registry authorization, and three additional agents. Six modules. The two UIs then share the same backend and the same agent registry but serve different personas with different capability palettes. The acceptance test for Phase 2 is walking the same household referral from the advisor's perspective and confirming the two-UI thesis holds.

| Phase | Modules | Use case |
|---|---|---|
| Phase 1 | 1–7 | Consumer Banker identifies and routes a wealth referral |
| Phase 2 | 8–13 | Wealth Advisor receives, prepares for, and tracks the referral |

## How to read the notebooks

Each Workshop 2 notebook follows the same five-section pattern as Workshop 1: the question that frames the module, the concept that answers it, the build that produces the artifact, the verification that proves the artifact works, and the "what just changed" bridge to the next module.

Read the concept sections carefully. The build cells produce the artifacts; the concept sections explain why the artifacts exist. A novice who runs all the cells but skips the concept sections will have a working deployment and no understanding of why it is built the way it is. The understanding is the goal.

When you are ready, confirm your prerequisites are met and proceed to [Module 1 — Pre-flight: Is Workshop 1 Ready?](../01-preflight/).
