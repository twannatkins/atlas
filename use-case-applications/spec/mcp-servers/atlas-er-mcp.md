# atlas-er-mcp

The MCP server that wraps AWS Entity Resolution lookups. Returns the canonical URI for a record from a source system.

## Purpose

When a record arrives from a source system (a row from an Iceberg table, an event from Kinesis), it carries the source system's internal identifier. The agents in Workshop 2 reason in terms of canonical URIs (`atlas:cust/9c2a1e`), not source IDs (`SAP_KNA1_4711837`). `atlas-er-mcp` resolves the translation.

## What it exposes

- `lookup(source_system, source_id)` — return the canonical URI for a known record.
- `resolve(record_attributes)` — submit a record's attributes to ER and receive a MatchID; the MatchID maps to a canonical URI in the SLGD.
- `link(source_record_uri, canonical_uri)` — record a verified link (used when human review confirms an uncertain match).

## What it does not do

- Does not mint new URIs without ER's MatchID confirmation
- Does not guess. If no match is found, returns `no_match` with diagnostic context.

## Dependencies

- AWS Entity Resolution workflow deployed for the institution's data
- The substitution guide covers the two paths: native AWS ER, or adapter to existing MDM
