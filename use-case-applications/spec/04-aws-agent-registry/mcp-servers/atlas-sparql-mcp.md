# atlas-sparql-mcp

The MCP server that wraps SPARQL access to the Neptune knowledge graph. The most-invoked server in Workshop 2 — every read agent and every write agent goes through it.

## Purpose

Agents need a stable, typed interface for SPARQL operations. Calling Neptune directly would require every agent to embed connection logic, IAM signing, error handling, and Lake Formation scope translation. `atlas-sparql-mcp` does all of that once.

## What it exposes

- `query(sparql, persona_claim)` — read-only SELECT/CONSTRUCT queries against the SLGD (or LGD when explicitly scoped). Persona claim is translated to Lake Formation scope on the federated path.
- `update(sparql, persona_claim)` — INSERT/DELETE operations. Requires the persona to have write authority for the affected named graph.
- `construct_and_validate(construct_sparql, shape_uri, persona_claim)` — runs a CONSTRUCT query and validates the result against a SHACL shape before returning. Used by signal-detection agents.

## What it does not do

- Does not query without a persona claim. Anonymous queries are rejected at the MCP boundary.
- Does not bypass Lake Formation. The federated path through Ontop respects LF tags.
- Does not commit triples that fail SHACL validation (when used via `construct_and_validate`).

## Dependencies

- Amazon Neptune cluster from Workshop 1 (`agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml`)
- Ontop on ECS Fargate (deployed by Workshop 2 CDK stack)
- `atlas-shacl-mcp` for the validation path
