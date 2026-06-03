"""Minimal atlas_sparql shim for AppSync resolver Lambdas — no rdflib dependency."""
from __future__ import annotations
import re

class AtlasSPARQLError(Exception):
    pass

_UNSAFE_URI_CHARS = re.compile(r'[<>{}\[\]`|^\\"\'\s]')
_SAFE_URI_PREFIXES = ("https://github.com/your-org/atlas/","http://www.w3.org/","https://spec.edmcouncil.org/fibo/","urn:atlas:",)
_SAFE_COMPACT_PREFIXES = ("atlas:","atlas-part-2:","fibo-","prov:","rdfs:","rdf:","skos:","dcat:",)

def safe_uri(uri: str, *, allow_any_scheme: bool = False) -> str:
    if not uri or not isinstance(uri, str):
        raise AtlasSPARQLError("URI must be a non-empty string")
    if _UNSAFE_URI_CHARS.search(uri):
        raise AtlasSPARQLError(f"URI contains unsafe characters: {uri!r}")
    if not allow_any_scheme:
        if not (any(uri.startswith(p) for p in _SAFE_URI_PREFIXES) or any(uri.startswith(p) for p in _SAFE_COMPACT_PREFIXES)):
            raise AtlasSPARQLError(f"URI does not start with a known ATLAS prefix: {uri!r}")
    return uri

def safe_int(value, *, min_val: int = 1, max_val: int = 1000, default: int = 20) -> int:
    try:
        return max(min_val, min(int(value), max_val))
    except (TypeError, ValueError):
        return default

def build_prefixes() -> str:
    return ("PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
            "PREFIX owl:  <http://www.w3.org/2002/07/owl#>\n"
            "PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>\n"
            "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
            "PREFIX dcat: <http://www.w3.org/ns/dcat#>\n"
            "PREFIX fibo-fnd-pty-pty: <https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Parties/>\n")

def prefixed(query_body: str) -> str:
    return build_prefixes() + "\n" + query_body
