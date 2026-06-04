#!/usr/bin/env python3
"""
load-ws2-ontology-concepts.py — WS2-owned loader for the atlas-part-2: signal-type
SKOS concepts.

WHY THIS EXISTS
  Workshop 1's loader (agentic-semantic-layer/notebooks/03_two_tier_neptune.ipynb)
  bulk-loads the WS1 ontology into the SLGD, but its file list is hardcoded and
  WS1-owned — it does not (and must not) reference Workshop 2 files. The WS2 signal
  concepts in ontology-extensions/signal-types.ttl (LargeInboundWire, SegmentShift,
  NoAdvisorCoverage, EngagementDecay, NetworkInfluence) were authored but never
  loaded, so their skos:prefLabels weren't in the SLGD and the resolver's label join
  fell back to the raw atlas-part-2: URI. This step closes that gap — WS2-owned, per
  the WS1-boundary rule (never edit agentic-semantic-layer/).

WHAT IT DOES
  Parses signal-types.ttl -> N-Triples -> a single INSERT DATA, executed against the
  SLGD. Idempotent: the concepts have fixed URIs, so re-running re-inserts identical
  triples (RDF set semantics) and the graph is unchanged.

  The INSERT carries the atlas: and prov: PREFIX declarations the atlas-sparql-mcp
  update op requires, even though N-Triples use full IRIs.

TRANSPORT
  This reference implementation prints the INSERT DATA query; execute it against the
  SLGD via whatever signed path the environment provides:
    - From SageMaker Studio (in-VPC): the WS1 sparql_update_slgd helper (SigV4 POST).
    - Out-of-VPC: the atlas-sparql-mcp `update` op with a Cognito JWT.
  Pass --emit to print the query for piping; the caller owns the write.

TEARDOWN (revert this load)
  DELETE every triple whose SUBJECT is under the part2# namespace — proven safe
  because WS1 concepts use the atlas: namespace, never part2:, so no WS1 triple
  matches:
    PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    DELETE { ?s ?p ?o }
    WHERE { ?s ?p ?o .
            FILTER(STRSTARTS(STR(?s), "https://github.com/your-org/atlas/ontology/part2#")) }
"""
from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph

TTL = Path(__file__).resolve().parents[1] / "ontology-extensions" / "signal-types.ttl"

# atlas-sparql-mcp requires these PREFIX declarations on every update (atlas_sparql.py
# _REQUIRED_PREFIX_DECLARATIONS). Declared-but-unused is harmless.
_PREAMBLE = (
    "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
    "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
    "PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>\n"
    "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
)


def build_insert() -> str:
    g = Graph()
    g.parse(str(TTL), format="turtle")
    lines = [
        l.strip()
        for l in g.serialize(format="nt").split("\n")
        if l.strip() and not l.startswith("#")
    ]
    return _PREAMBLE + "INSERT DATA {\n" + "\n".join(lines) + "\n}"


if __name__ == "__main__":
    query = build_insert()
    n = query.count("\n") - _PREAMBLE.count("\n") - 1
    sys.stderr.write(f"[load-ws2-concepts] {n} triples from {TTL.name}\n")
    print(query)  # caller pipes this to the signed SLGD update path
