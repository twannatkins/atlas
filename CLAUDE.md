# CLAUDE.md — ATLAS umbrella

This repository contains two workshops, each with its own build directives.

If you are working in `agentic-semantic-layer/`, see [`agentic-semantic-layer/CLAUDE.md`](./agentic-semantic-layer/CLAUDE.md).

If you are working in `use-case-applications/`, see [`use-case-applications/CLAUDE.md`](./use-case-applications/CLAUDE.md).

## Cross-workshop principles

A small number of principles apply to both workshops. Read these once, then defer to the workshop-specific directives.

**The workshops are sequential.** Workshop 1 (`agentic-semantic-layer/`) builds the FIBO-aligned ontology, SHACL shapes, R2RML mappings, and two-tier Neptune deployment. Workshop 2 (`use-case-applications/`) builds agents, MCP servers, GraphQL API, and two React UIs on top of Workshop 1. Workshop 2 never modifies Workshop 1.

**Both workshops teach.** Neither workshop is a build script. Both are taught through Jupyter notebooks that follow a question → concept → build → verification → what-just-changed pattern. When generating notebook content, the explanation is as important as the code. A novice reading the notebook should leave understanding *why* each piece exists.

**The ontology is the contract.** Workshop 1's ontology in `agentic-semantic-layer/ontology/` is the contract between the two workshops. Workshop 2's GraphQL schema, SPARQL queries, and component fragments are all written against the class names defined in Workshop 1. The contract is documented in `use-case-applications/spec/03-data-contracts.md`.

**Regulatory framing is explicit.** ATLAS is built for financial services and references specific regulations (SR 11-7, OCC 2011-12, 31 U.S.C. §5318(g)(2)). These references are teaching anchors, not legal disclaimers — they explain *why* the architecture is the way it is. Preserve them.

**Sentence case, lowercase-hyphenated filenames, snake_case notebooks.** Matches both workshops' existing conventions.

## When in doubt

Read the workshop's own CLAUDE.md. If it doesn't address the question, the spec section it points to does.
