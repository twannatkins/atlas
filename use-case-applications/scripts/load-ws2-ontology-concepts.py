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
  Parses signal-types.ttl and CONVERGES the SLGD's atlas-part-2: concepts to it:
  build_reload() returns [DELETE the part2# namespace, INSERT the file's triples].
  Running both in order makes the SLGD match the file exactly, every time.

  Why not a bare INSERT: a bare INSERT is idempotent only for UNCHANGED triples (RDF
  set semantics dedupes identical ones). After a literal edit — e.g. changing a
  concept's rdfs:comment — re-loading would leave BOTH the old and the new value
  (they are distinct triples). Clearing the namespace first guarantees convergence.

  Both statements carry the atlas: and prov: PREFIX declarations the atlas-sparql-mcp
  update op requires, even though N-Triples use full IRIs. The DELETE is scoped to the
  part2# subject namespace (proven safe — no WS1 triple is under it); it is never
  scoped by skos:inScheme, which would clip WS1's five concepts.

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


def _insert_body() -> str:
    """The current file's triples as an INSERT DATA body (with prefixes)."""
    g = Graph()
    g.parse(str(TTL), format="turtle")
    lines = [
        l.strip()
        for l in g.serialize(format="nt").split("\n")
        if l.strip() and not l.startswith("#")
    ]
    return _PREAMBLE + "INSERT DATA {\n" + "\n".join(lines) + "\n}"


def build_delete_namespace() -> str:
    """DELETE every triple whose SUBJECT is under the atlas-part-2: namespace.

    This is the proven-safe teardown scope (Pass 2a): WS1 concepts use the atlas:
    namespace, never part2:, so no Workshop 1 triple matches. It is NOT scoped by
    skos:inScheme — that would also match WS1's five concepts (which are inScheme the
    same WealthSignalTypeScheme) and clip them. Namespace prefix only.
    """
    return _PREAMBLE + (
        "DELETE { ?s ?p ?o }\n"
        "WHERE { ?s ?p ?o . "
        'FILTER(STRSTARTS(STR(?s), "https://github.com/your-org/atlas/ontology/part2#")) }'
    )


def build_reload() -> list[str]:
    """The idempotent load: clear the part2# namespace, then insert the file's triples.

    Returned as an ordered [DELETE, INSERT] pair for the caller to execute in sequence.
    A bare INSERT is NOT idempotent after a literal edit — re-loading after changing,
    say, a concept's rdfs:comment leaves BOTH the old and new value (RDF set semantics
    dedupes only identical triples). Clearing the namespace first makes the load
    CONVERGE to exactly what the file says, every run.
    """
    return [build_delete_namespace(), _insert_body()]


def build_insert() -> str:
    """Backwards-compatible: the INSERT body only. Prefer build_reload() for an
    idempotent, converge-to-file load."""
    return _insert_body()


if __name__ == "__main__":
    # Emit the converge-to-file reload: DELETE the namespace, then INSERT the file.
    statements = build_reload()
    n = statements[1].count("\n") - _PREAMBLE.count("\n") - 1
    sys.stderr.write(
        f"[load-ws2-concepts] reload = DELETE part2# namespace, then INSERT {n} "
        f"triples from {TTL.name}\n"
    )
    for stmt in statements:
        print(stmt)
        print("---")  # statement separator for the caller
