# atlas-shacl-mcp

The MCP server that wraps SHACL shape validation. Workshop 1 ships six shapes; this server exposes them for runtime validation.

## Purpose

Every signal-producing agent in Workshop 2 needs to validate its output before committing triples. Embedding SHACL validation logic in every agent would mean every agent loads the shapes, parses them, and re-implements validation. `atlas-shacl-mcp` does it once.

## What it exposes

- `validate(triples, shape_uris)` — run the named shapes against a set of triples. Returns a conformance report.
- `validate_graph(named_graph, shape_uris)` — validate an entire named graph (used in pre-flight checks).
- `list_shapes()` — return the catalog of available shapes for introspection.

## What it does not do

- Does not modify shapes at runtime. Shapes are versioned artifacts in `agentic-semantic-layer/ontology/atlas-shapes.ttl`.
- Does not commit triples on validation success. Validation is a separate step from commit.

## Dependencies

- `agentic-semantic-layer/ontology/atlas-shapes.ttl` loaded into Neptune
- pyshacl or equivalent SHACL engine in the Lambda runtime
