#!/usr/bin/env python3
"""
derive-no-advisor-coverage.py — WS2-owned derivation of the gate-C
atlas-part-2:NoAdvisorCoverageSignal.

This script makes the live derivation reproducible from the repo. It mirrors exactly
the logic that wrote the 40 NoAdvisorCoverage signals to the SLGD in Pass 2b.

PRINCIPLE: derive, don't insert. A signal fires from a real, queryable fact through
a rule, is SHACL-validated, and is written only if conformant. No signal is
hand-placed; no evidence or date is fabricated.

GATE C — why coverage-absence alone is not a signal
  A plain "no advisor coverage" NOT-EXISTS fires for ~120 of 200 customers (60%) —
  that is a census of the uncovered, not a signal. Gate C makes it a signal: it
  fires only for a customer who is ALREADY wealth-signalled (produces at least one
  other WealthSignal) AND has no active coverage. That is a coverage gap that
  matters — a wealth-eligible customer a referral could serve. Fires for 40
  customers in the synthetic SLGD (incl. demo customer c6b6e4ad, which produces a
  LargeDepositPattern signal and has no advisor).

ORDERING (load-bearing)
  Gate C reads "?customer atlas:producesSignal ?anySig", so the OTHER signals
  (LargeDepositPattern, HouseholdAggregation) must already be PERSISTED in the SLGD
  before this runs. In the Workshop 1 derivation cell, place this AFTER the LDP and
  HouseholdAggregation inserts. If it runs before they persist, gate C matches
  nobody and fires zero — a silent failure. The caller MUST enforce this order.

ABSENCE-SIGNAL TRIPLE TEMPLATE (no fabrication)
  An absence signal has no positive evidence and no event date. It carries only:
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas-part-2:NoAdvisorCoverageSignal ;   # required by shape
            prov:wasGeneratedBy <inst:signal-derivation-run> .           # so teardown removes it
    ?customer atlas:producesSignal ?signal .                             # so the card finds it
  evidencedBy is OMITTED (no transaction); signalDate is OMITTED (no event date).
  WealthSignalTypeShape (the only shape targeting atlas:WealthSignal) requires only
  one hasSignalType, so this conforms. URI pattern: signal-nac-<hex>.

  PRECONDITION: atlas-part-2:NoAdvisorCoverageSignal must be loaded in the SLGD
  (run load-ws2-ontology-concepts.py first) so the signal's type — and the card's
  label join — resolve.

VALIDATE-BEFORE-WRITE
  validate_signals() runs pyshacl against Workshop 1's atlas-shapes.ttl and returns
  the N-Triples ONLY if the candidate graph conforms. The caller writes the returned
  triples and nothing if it raises — identical discipline to the WS1 derivation
  cell's _validate_and_insert, just packaged for WS2 reuse. SHACL rejection must
  HALT the write, never be loosened.

TEARDOWN (revert this derivation)
  The signals carry the signal-derivation-run stamp and the NoAdvisorCoverageSignal
  type, so this surgical DELETE removes exactly them and nothing WS1:
    PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    DELETE { ?signal ?sp ?so . ?customer atlas:producesSignal ?signal . }
    WHERE { ?signal atlas:hasSignalType atlas-part-2:NoAdvisorCoverageSignal ;
                    prov:wasGeneratedBy <https://github.com/your-org/atlas/instance#signal-derivation-run> ;
                    ?sp ?so .
            OPTIONAL { ?customer atlas:producesSignal ?signal } }

TRANSPORT
  Like the WS1 derivation, the actual SLGD reads/writes go through whatever signed
  path the environment provides (in-VPC SigV4 from Studio, or the atlas-sparql-mcp
  query/update ops with a Cognito JWT out-of-VPC). This module is transport-agnostic:
  pass in a `query(sparql)->rows` callable; it returns validated N-Triples for the
  caller to write. It performs no I/O of its own beyond loading the shapes file.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable, List

from rdflib import Graph
import pyshacl

ATLAS = "https://github.com/your-org/atlas/ontology#"
PART2 = "https://github.com/your-org/atlas/ontology/part2#"
PROV = "http://www.w3.org/ns/prov#"
INST = "https://github.com/your-org/atlas/instance#"
DERIVATION_RUN = f"{INST}signal-derivation-run"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# WS1 shapes — the validate-before-write gate. WS2 reads WS1's shapes read-only;
# it never modifies them.
SHAPES = Path(__file__).resolve().parents[2] / "agentic-semantic-layer" / "ontology" / "atlas-shapes.ttl"

# Gate-C candidate query: customers who are uncovered (no active AdvisoryRelationship)
# AND already produce at least one WealthSignal. "Active" = a hasAdvisor relationship
# with no coverageEndDate (mirrors the LargeDepositPattern CONSTRUCT's coverage clause).
CANDIDATE_QUERY = """
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
SELECT DISTINCT ?customer WHERE {
    ?customer a atlas:Customer ;
              atlas:producesSignal ?anySig .
    FILTER NOT EXISTS {
        ?customer atlas:hasAdvisor ?rel .
        FILTER NOT EXISTS { ?rel atlas:coverageEndDate ?end }
    }
}
"""


def build_signal_triples(customer_uris: List[str]) -> List[str]:
    """Mint the absence-signal N-Triples for each qualifying customer."""
    lines: List[str] = []
    for c in customer_uris:
        sig = f"{INST}signal-nac-{uuid.uuid4().hex[:12]}"
        lines.append(f"<{sig}> <{RDF_TYPE}> <{ATLAS}WealthSignal> .")
        lines.append(f"<{sig}> <{ATLAS}hasSignalType> <{PART2}NoAdvisorCoverageSignal> .")
        lines.append(f"<{sig}> <{PROV}wasGeneratedBy> <{DERIVATION_RUN}> .")
        lines.append(f"<{c}> <{ATLAS}producesSignal> <{sig}> .")
    return lines


def validate_signals(triples_nt: List[str]) -> List[str]:
    """pyshacl-validate the candidate signal triples against WealthSignalTypeShape.

    Returns the triples if the candidate graph conforms; raises RuntimeError if it
    does not (the caller must NOT write on rejection, and must NOT loosen the shape).
    """
    if not triples_nt:
        return []
    candidate = Graph()
    for t in triples_nt:
        candidate.parse(data=t, format="nt")
    if len(candidate) == 0:
        raise RuntimeError("candidate graph empty — triples failed to parse; not writing")
    shapes = Graph()
    shapes.parse(str(SHAPES), format="turtle")
    conforms, _, report = pyshacl.validate(candidate, shacl_graph=shapes, inference="rdfs")
    if not conforms:
        raise RuntimeError(f"SHACL rejected NoAdvisorCoverage signals — not writing:\n{report[:600]}")
    return triples_nt


def derive(query: Callable[[str], List[dict]]) -> List[str]:
    """Run gate C against the live SLGD (via the caller's query callable) and return
    SHACL-validated N-Triples ready to INSERT. Performs no writes.

    `query(sparql)` must return a list of binding dicts (e.g. [{"customer": "<uri>"}]).
    """
    rows = query(CANDIDATE_QUERY)
    customers = [r["customer"] for r in rows if r.get("customer")]
    triples = build_signal_triples(customers)
    validated = validate_signals(triples)  # raises on non-conformance
    return validated


def insert_query(validated_nt: List[str]) -> str:
    """Wrap validated triples in an INSERT DATA carrying the prefixes the
    atlas-sparql-mcp update op requires (atlas:, prov:)."""
    preamble = (
        "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
    )
    return preamble + "INSERT DATA {\n" + "\n".join(validated_nt) + "\n}"


if __name__ == "__main__":
    # Reference usage (no I/O here): the caller supplies a signed `query` callable,
    # then writes insert_query(derive(query)) via the same signed path. Example:
    #
    #   from derive_no_advisor_coverage import derive, insert_query
    #   validated = derive(lambda sparql: run_select(sparql))   # gate C + pyshacl gate
    #   run_update(insert_query(validated))                      # write only if validated
    #
    # Run load-ws2-ontology-concepts.py FIRST (the type/label must be loaded), and
    # run this AFTER the LargeDepositPattern + HouseholdAggregation inserts persist.
    print(__doc__)
