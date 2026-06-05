# wealth-signal-detector

Detects wealth-readiness signals in customer behavior by running SPARQL CONSTRUCT queries that produce `atlas:WealthSignal` instances. These signals populate the Wholesale UI's Referral Detail screen.

## Purpose

A wealth signal is a structured assertion that a customer or household has exhibited behavior consistent with wealth readiness — for example a large inbound deposit, or an absence of advisor coverage despite eligibility. The signal is not a recommendation; it is *evidence* a banker uses to decide whether to route a referral.

`wealth-signal-detector` runs the SPARQL CONSTRUCT queries that produce these signals. The queries are stored alongside the agent and are versioned with the same change-management process as code.

## Posture

**Deterministic, SHACL-driven.** The agent runs deterministic SPARQL CONSTRUCT queries. The output triples are validated against `atlas:WealthSignalTypeShape` and `atlas:ProvenanceShape` before being written to the graph. Any triple that fails validation is rejected with a diagnostic; nothing partial is committed.

## What it does

1. Receives a target (a customer URI, a household URI, or a scope predicate).
2. Loads the SPARQL CONSTRUCT queries for each registered signal type.
3. Executes each CONSTRUCT query against the SLGD.
4. Validates the resulting triples via `atlas-shacl-mcp`.
5. Writes validated triples to the SLGD via `atlas-sparql-mcp`.
6. Returns a list of signal URIs that were minted, with provenance.

## What it does not do

- Does not write triples that fail SHACL validation
- Does not interpret what the signals mean (that's `referral-rationale-drafter`'s job)
- Does not route referrals (that's `referral-orchestrator`'s job)

## Where the novice meets this

Notebook `01_why_agents.ipynb` introduces the pattern. The agent is fully exercised in Phase 1's end-to-end walkthrough in `07_phase_1_acceptance.ipynb`.

## Signals it detects (Phase 1)

| Signal type | What it detects | Status |
|---|---|---|
| `atlas:LargeDepositPattern` | Deposit ≥ threshold in window, no active coverage (Workshop 1 derivation) | Live (Phase 1) |
| `atlas-part-2:NoAdvisorCoverageSignal` | Wealth-eligible (already-signalled) customer without active `atlas:AdvisoryRelationship` | Live (Phase 1) |
| `atlas-part-2:SegmentShiftSignal` | Transaction velocity crossing a segment tier boundary | Deferred — needs the segment/tier model + temporal data of the session-intelligence phase; not derivable from Phase-1 data |

Phase 2 adds two more signals (`EngagementDecaySignal`, `NetworkInfluenceSignal`) detected by `behavioral-signal-agent`. See `notebooks/phase-1-referral/05_wealth_signals.ipynb` for how the live signals are derived and why Segment Shift is honestly deferred rather than faked.

## Dependencies

- `atlas-sparql-mcp` for query execution
- `atlas-shacl-mcp` for shape validation
- `agentic-semantic-layer/ontology/atlas-shapes.ttl` for the validating shapes
