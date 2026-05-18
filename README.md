# ATLAS

**Adaptive Truist Linked Analytics System — an AWS-native reference architecture for governed agentic AI on enterprise data.**

ATLAS is delivered as two workshops. You work through them in order. By the end, you have a working, governed, agent-driven application stack that runs entirely on AWS, aligned to FSI standards, and ready to adapt to your institution's use cases.

## The two workshops

### Workshop 1 — Building a Semantic Layer for Agentic AI

*Directory: [`agentic-semantic-layer/`](./agentic-semantic-layer/)*

You build an **ontology** for financial services, aligned to the Financial Industry Business Ontology (FIBO), with SHACL boundary shapes that enforce what must be true for data to enter the graph. You learn the federation patterns that let enterprise data sources participate in the ontology without bulk migration, and you stand up a two-tier Neptune deployment that hosts the working knowledge graph.

By the end of Workshop 1, you have a semantic layer that AI agents can navigate reliably, deterministically, and within model risk policy. This is the substrate everything else in ATLAS depends on.

**Time:** One full day. **Audience:** FSI engineers, AWS Solutions Architects, ontology novices.

### Workshop 2 — Use Case Applications

*Directory: [`use-case-applications/`](./use-case-applications/)*

You take the substrate from Workshop 1 and build two working banking applications on top of it: a Wholesale UI for Consumer Banker referrals and a Wealth UI for the Wealth Advisor workbench. Both are backed by registered agents and MCP servers, both consume the same FIBO-shaped GraphQL API, and both demonstrate the four-layer permission model that makes governed agentic AI possible.

By the end of Workshop 2, you have two production-grade React applications, eight registered agents, five registered MCP servers, and a complete blueprint for adapting any FSI use case to the ATLAS substrate.

**Time:** One full day (Phase 1) plus self-paced extension (Phase 2). **Prerequisite:** Workshop 1 complete.

## The journey

The two workshops are designed to be read and built in order. Workshop 1 builds the foundation; Workshop 2 builds the things that use the foundation. Skipping Workshop 1 is not supported — Workshop 2's pre-flight notebook checks that Workshop 1's artifacts are loaded and refuses to start without them.

If you are evaluating ATLAS as a customer reference, read the top-level README of each workshop first. They explain what you'll build and why it matters before you write any code.

If you are building, start with Workshop 1's [introduction](./agentic-semantic-layer/workshop/content/00-introduction/index.md).

## Why ATLAS exists

Enterprise AI agents in regulated industries face a structural problem: language models hallucinate, and hallucinations are unacceptable when the answer feeds a compliance decision, a referral routing, or a wealth recommendation. The industry solution to this problem is to ground agents in a governed knowledge layer — an ontology with explicit semantics, deterministic validation, and full provenance — rather than letting them reason directly over raw enterprise data.

ATLAS builds that layer on AWS, aligned to FIBO, with SHACL drawing the boundary between deterministic rules and probabilistic reasoning. The two workshops teach the construction and the application, in that order.

## What's in the repository

```
atlas/
├── agentic-semantic-layer/      # Workshop 1: the FIBO-aligned ontology and the substrate agents operate on
├── use-case-applications/       # Workshop 2: the registered agents, the GraphQL API, and the two UIs
├── CLAUDE.md                    # Build directives for Claude Code (umbrella, defers to each workshop)
├── LICENSE                      # MIT-0
└── README.md                    # This file
```

Each workshop has its own README, its own CLAUDE.md, its own notebooks, and its own Workshop Studio content. They are independent enough to read separately, but they are designed to be experienced sequentially.

## License

MIT-0. See [LICENSE](./LICENSE).
