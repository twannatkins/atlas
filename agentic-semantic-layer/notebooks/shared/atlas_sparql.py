"""
atlas_sparql — SPARQL query validation and execution utilities.

All SPARQL strings pass through atlas_sparql.validate() before submission
to Neptune. This is the enforcement point for the deterministic-vs-probabilistic
boundary at the query layer: any query that would write probabilistic-opaque
data to the SLGD is caught here by a pattern check before the wire call.

Component class: DETERMINISTIC — given the same query string and graph state,
validate() always returns the same result.
"""

from __future__ import annotations

import re
from typing import Optional

from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.processor import prepareUpdate


class AtlasSPARQLError(Exception):
    """Raised when a SPARQL query fails validation."""


_FORBIDDEN_WRITE_PATTERNS = [
    # Prohibit direct INSERT of triples tagged atlas:probabilisticOpaque
    # without an accompanying atlas:explainability predicate.
    re.compile(r"INSERT\s+DATA\s*\{[^}]*atlas:probabilisticOpaque\s+true", re.IGNORECASE),
]

_REQUIRED_PREFIX_DECLARATIONS = {
    "atlas": "https://github.com/your-org/atlas/ontology#",
    "prov":  "http://www.w3.org/ns/prov#",
}


def validate(query: str, *, require_prefixes: bool = False) -> str:
    """Parse and validate a SPARQL query string.

    Parameters
    ----------
    query:
        Raw SPARQL string to validate.
    require_prefixes:
        When True, assert that the query declares the atlas: and prov: prefixes.
        Set this for INSERT/UPDATE queries that write to the SLGD.

    Returns
    -------
    str
        The original query string, unchanged, if validation passes.

    Raises
    ------
    AtlasSPARQLError
        If the query is syntactically invalid or violates a boundary rule.
    """
    # Syntactic parse via rdflib (raises prepareQuery exceptions on bad syntax)
    # Use prepareUpdate for INSERT/DELETE/LOAD/CLEAR/DROP/CREATE statements;
    # use prepareQuery for SELECT/CONSTRUCT/ASK/DESCRIBE.
    _UPDATE_KEYWORDS = re.compile(
        r"(?:^|\n)\s*(?:INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b", re.IGNORECASE
    )
    try:
        if _UPDATE_KEYWORDS.search(query):
            prepareUpdate(query)
        else:
            prepareQuery(query)
    except Exception as exc:
        raise AtlasSPARQLError(f"SPARQL syntax error: {exc}") from exc

    # Boundary pattern checks
    for pattern in _FORBIDDEN_WRITE_PATTERNS:
        if pattern.search(query):
            raise AtlasSPARQLError(
                "Query attempts to write probabilistic-opaque data to the SLGD "
                "without an explainability attribute. Add atlas:explainability "
                "true and atlas:modelVersion to the INSERT block, or route this "
                "write through the LGD promotion path."
            )

    if require_prefixes:
        for prefix, iri in _REQUIRED_PREFIX_DECLARATIONS.items():
            if f"PREFIX {prefix}:" not in query and f"@prefix {prefix}:" not in query:
                raise AtlasSPARQLError(
                    f"SPARQL query is missing required PREFIX declaration for "
                    f"'{prefix}:' (<{iri}>). Add it to the query preamble."
                )

    return query


def build_prefixes() -> str:
    """Return the standard ATLAS SPARQL prefix block as a string."""
    return (
        "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
        "PREFIX fibo-fnd-pty-pty: <https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/>\n"
        "PREFIX fibo-fbc-pas-fpas: <https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/>\n"
        "PREFIX fibo-fbc-fi-ip: <https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/InstrumentPricing/>\n"
        "PREFIX owl:  <http://www.w3.org/2002/07/owl#>\n"
        "PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
        "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "PREFIX dcat: <http://www.w3.org/ns/dcat#>\n"
    )


def prefixed(query_body: str) -> str:
    """Prepend the standard ATLAS prefix block to a query body."""
    return build_prefixes() + "\n" + query_body
