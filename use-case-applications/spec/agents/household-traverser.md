# household-traverser

Returns a 1-hop relationship strip for the inline graph view in the Wholesale UI's Referral Detail screen. The simplest agent in Phase 1, and the right one to study to understand the read-only SPARQL pattern.

## Purpose

When a Consumer Banker opens a household's referral detail, the UI shows a relationship strip: the primary customer, the household members, the related accounts, the relevant external entities. This is a 1-hop graph traversal from the household node. `household-traverser` runs that traversal and returns the nodes.

## Posture

**Read-only, SPARQL.** The agent executes a single parameterized SPARQL query, returns the rows, and writes nothing. There is no state to corrupt. There is no decision to audit beyond the query and its result.

## What it does

1. Receives a household URI and the user's persona claim.
2. Executes a parameterized SPARQL query that returns 1-hop neighbors with their type and labels.
3. Returns the rows.

## What it does not do

- Does not traverse beyond 1 hop. Deeper traversals are explicit user actions, not implicit defaults.
- Does not interpret relationships. The agent returns *what is connected*; the UI decides *how to render*.
- Does not write to the graph.

## Where the novice meets this

Notebook `01_why_agents.ipynb` introduces the read-only SPARQL pattern. The agent is the simplest example of it.

## Dependencies

- `atlas-sparql-mcp` for query execution
