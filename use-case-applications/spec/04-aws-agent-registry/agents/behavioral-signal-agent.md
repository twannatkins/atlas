# behavioral-signal-agent (Phase 2)

Detects behavioral signals derived from clickstream and cross-LOB graph traversal. Phase 2 only. Extends the deterministic signal-detection pattern from `wealth-signal-detector` with new signal types backed by LGD-derived data.

## Purpose

The Wealth UI surfaces signals that traditional CRMs cannot — `EngagementDecaySignal` (the customer's portal usage is declining) and `NetworkInfluenceSignal` (a household member is newly connected to a commercial banker for a related entity). These signals require data that does not exist in the SLGD: clickstream events and cross-LOB graph traversals. `behavioral-signal-agent` produces them.

## Posture

**Deterministic, runs over LGD-derived sessions.** Same posture as `wealth-signal-detector`. Same SHACL validation. The only difference is the data the agent reads — it queries the LGD (the lexical/raw tier) for clickstream events, then writes derived signals to the SLGD.

## What it does

1. Receives a customer URI and the user's persona claim.
2. Executes SPARQL CONSTRUCT queries that derive `atlas-part-2:Session` instances from raw clickstream events in the LGD.
3. Computes engagement decay over the session set.
4. Traverses cross-LOB connections in the SLGD to identify network influence.
5. Mints signals via `atlas:WealthSignalTypeShape`-validated triples.

## What it does not do

- Does not store raw clickstream in the SLGD. The SLGD holds derived signals; the LGD holds raw events. The two-tier separation is what makes this clean.
- Does not retain session data beyond the analysis window.

## Dependencies

- `atlas-sparql-mcp` (queries both LGD and SLGD)
- `atlas-shacl-mcp` for validation
- Workshop 2 ontology extensions: `atlas-part-2:Session`, `atlas-part-2:NetworkContact`
