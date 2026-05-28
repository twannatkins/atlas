"""
atlas_sparql — SPARQL query validation and execution utilities.

All SPARQL strings pass through atlas_sparql.validate() before submission
to Neptune. This is the enforcement point for the deterministic-vs-probabilistic
boundary at the query layer: any query that would write probabilistic-opaque
data to the SLGD is caught here by a pattern check before the wire call.

URI parameters are sanitized via atlas_sparql.safe_uri() before interpolation
into query templates. This prevents SPARQL injection by rejecting URIs that
contain characters capable of breaking out of an IRI reference (<...>).

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


# ---------------------------------------------------------------------------
# URI sanitization — prevents SPARQL injection via crafted IRI values
# ---------------------------------------------------------------------------

# Valid IRI characters per RFC 3987. We reject anything that could close an
# IRI reference or inject SPARQL syntax: angle brackets, braces, backtick,
# pipe, caret, whitespace, and quotes. The hash character (#) is permitted
# because it is a standard fragment separator in RDF namespace IRIs.
_UNSAFE_URI_CHARS = re.compile(r'[<>{}\[\]`|^\\"\'\s]')

# Known safe namespace prefixes for ATLAS URIs
_SAFE_URI_PREFIXES = (
    "https://github.com/your-org/atlas/",
    "http://www.w3.org/",
    "https://spec.edmcouncil.org/fibo/",
    "urn:atlas:",
)

# Compact prefix forms used in GraphQL arguments (resolved by SPARQL PREFIX declarations)
_SAFE_COMPACT_PREFIXES = (
    "atlas:",
    "atlas-part-2:",
    "fibo-",
    "prov:",
    "rdfs:",
    "rdf:",
    "skos:",
    "dcat:",
)


def safe_uri(uri: str, *, allow_any_scheme: bool = False) -> str:
    """Validate and return a URI safe for interpolation into SPARQL queries.

    Parameters
    ----------
    uri:
        The URI string to validate. Can be a full IRI
        (https://github.com/your-org/atlas/instance#customer-123) or a
        compact prefixed name (atlas:cust/9c2a1e) that will be resolved
        by SPARQL PREFIX declarations.
    allow_any_scheme:
        When False (default), the URI must start with one of the known ATLAS
        namespace prefixes or compact prefix forms. Set True for URIs from
        trusted internal sources (e.g., Entity Resolution canonical URIs).

    Returns
    -------
    str
        The original URI string if it passes validation.

    Raises
    ------
    AtlasSPARQLError
        If the URI contains unsafe characters or does not match a known prefix.
    """
    if not uri or not isinstance(uri, str):
        raise AtlasSPARQLError("URI must be a non-empty string")

    if _UNSAFE_URI_CHARS.search(uri):
        raise AtlasSPARQLError(
            f"URI contains characters that are not permitted in an IRI reference: "
            f"{uri!r}"
        )

    if not allow_any_scheme:
        is_safe = (
            any(uri.startswith(prefix) for prefix in _SAFE_URI_PREFIXES) or
            any(uri.startswith(prefix) for prefix in _SAFE_COMPACT_PREFIXES)
        )
        if not is_safe:
            raise AtlasSPARQLError(
                f"URI does not start with a known ATLAS namespace prefix: {uri!r}. "
                f"Expected one of: {_SAFE_URI_PREFIXES + _SAFE_COMPACT_PREFIXES}"
            )

    return uri


def safe_int(value, *, min_val: int = 1, max_val: int = 1000, default: int = 20) -> int:
    """Coerce a value to a bounded integer, safe for use in SPARQL LIMIT clauses.

    Parameters
    ----------
    value:
        The value to coerce (typically from user input).
    min_val:
        Minimum allowed value.
    max_val:
        Maximum allowed value (prevents unbounded result sets).
    default:
        Value to use if coercion fails.

    Returns
    -------
    int
        A bounded integer safe for interpolation into SPARQL.
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_val, min(n, max_val))


_FORBIDDEN_WRITE_PATTERNS = [
    # Pattern 1: Prohibit direct INSERT of triples tagged atlas:probabilisticOpaque
    # without an accompanying atlas:explainability predicate.
    (
        re.compile(r"INSERT\s+DATA\s*\{[^}]*atlas:probabilisticOpaque\s+true", re.IGNORECASE),
        "INSERT contains atlas:probabilisticOpaque=true without atlas:explainability. "
        "Probabilistic-opaque writes are not permitted at the SLGD boundary. "
        "Either route through the LGD promotion path (Module 5) or add "
        "atlas:explainability=true with a verified atlas:modelVersion."
    ),
    # Pattern 2: Reject any SPARQL write operation from LLM-generated queries.
    # The LLM at the edges (Module 7) translates natural language to SELECT
    # queries only. Any INSERT, DELETE, UPDATE, DROP, CLEAR, CREATE, LOAD,
    # COPY, MOVE, or ADD operation is a violation of the bounded-LLM contract.
    (
        re.compile(
            r"(?:^|\n|\s)(?:INSERT\s+DATA|INSERT\s+WHERE|INSERT\s*\{|"
            r"DELETE\s+DATA|DELETE\s+WHERE|DELETE\s*\{|"
            r"DROP\s+(?:GRAPH|ALL|NAMED|DEFAULT|SILENT)|"
            r"CLEAR\s+(?:GRAPH|ALL|NAMED|DEFAULT|SILENT)|"
            r"CREATE\s+(?:GRAPH|SILENT)|LOAD\s+(?:SILENT\s+)?<|"
            r"COPY\s+|MOVE\s+|ADD\s+(?:SILENT\s+)?)",
            re.IGNORECASE
        ),
        "Query contains a SPARQL write operation (INSERT/DELETE/DROP/CLEAR/"
        "CREATE/LOAD/COPY/MOVE/ADD). The bounded-LLM contract permits only "
        "SELECT/CONSTRUCT/ASK/DESCRIBE queries. If this is a legitimate write, "
        "route it through the Module 5 promotion path with PROV-O attribution, "
        "not through the NL-to-SPARQL component."
    ),
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
    # Update-vs-query dispatch: match SPARQL update keywords followed by their
    # required syntactic tokens (DATA/WHERE/{/etc) anywhere in the query string,
    # not just at the start of a line. This handles PREFIX-prefixed queries
    # (e.g., "PREFIX atlas: <...> INSERT DATA { ... }") where the update
    # keyword appears mid-line after the PREFIX declaration. Each branch
    # requires syntactically-meaningful following tokens, eliminating false
    # positives on SELECT queries that might contain bare words like "INSERT"
    # inside string literals.
    _UPDATE_KEYWORDS = re.compile(
        r"\b(?:"
        r"INSERT\s+(?:DATA|INTO)|INSERT\s*\{|"
        r"DELETE\s+(?:DATA|WHERE)|DELETE\s*\{|"
        r"LOAD\s+|CLEAR\s+|DROP\s+|"
        r"CREATE\s+|COPY\s+|MOVE\s+|ADD\s+"
        r")",
        re.IGNORECASE
    )
    try:
        if _UPDATE_KEYWORDS.search(query):
            prepareUpdate(query)
        else:
            prepareQuery(query)
    except Exception as exc:
        raise AtlasSPARQLError(f"SPARQL syntax error: {exc}") from exc

    # Boundary pattern checks: reject queries that violate the deterministic-
    # vs-probabilistic boundary or that perform unauthorized writes.
    for pattern, message in _FORBIDDEN_WRITE_PATTERNS:
        if pattern.search(query):
            raise AtlasSPARQLError(message)

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
