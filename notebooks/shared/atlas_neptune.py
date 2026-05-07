"""
atlas_neptune — thin Neptune SPARQL endpoint client.

Wraps the Neptune SPARQL HTTP endpoint. All queries pass through
atlas_sparql.validate() before submission. The client is intentionally
thin: it does not retry on failure, does not cache results, and does
not manage connections beyond what the requests library provides.

Component class: DETERMINISTIC — given the same endpoint state and
query, the client always submits the same wire request and returns
the same parsed response.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from atlas_sparql import validate, AtlasSPARQLError


class NeptuneClient:
    """SPARQL client for an Amazon Neptune endpoint.

    Parameters
    ----------
    endpoint:
        Neptune cluster endpoint hostname, e.g.
        ``my-cluster.cluster-xxxx.us-east-1.neptune.amazonaws.com``.
        If omitted, reads from the environment variable
        ``ATLAS_NEPTUNE_ENDPOINT``.
    port:
        Neptune SPARQL port. Default 8182.
    use_https:
        Whether to use HTTPS. Default True.
    timeout:
        Request timeout in seconds. Default 30.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        port: int = 8182,
        use_https: bool = True,
        timeout: int = 30,
    ) -> None:
        host = endpoint or os.environ.get("ATLAS_NEPTUNE_ENDPOINT")
        if not host:
            raise ValueError(
                "Neptune endpoint not specified. Pass 'endpoint=' or set "
                "the ATLAS_NEPTUNE_ENDPOINT environment variable."
            )
        scheme = "https" if use_https else "http"
        self._sparql_url = f"{scheme}://{host}:{port}/sparql"
        self._timeout = timeout

    def query(self, sparql: str, named_graph: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a SPARQL SELECT query and return bindings as a list of dicts.

        Parameters
        ----------
        sparql:
            SPARQL SELECT query string. Validated before submission.
        named_graph:
            Optional named graph IRI to scope the query with a
            FROM <named_graph> clause.

        Returns
        -------
        list[dict]
            Each item maps variable names to binding values.
        """
        validated = validate(sparql)
        if named_graph:
            validated = f"FROM <{named_graph}>\n{validated}"

        response = requests.get(
            self._sparql_url,
            params={"query": validated},
            headers={"Accept": "application/sparql-results+json"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        vars_ = data["results"]["head"]["vars"]
        return [
            {v: b[v]["value"] if v in b else None for v in vars_}
            for b in data["results"]["bindings"]
        ]

    def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE (INSERT/DELETE) statement.

        Requires atlas: and prov: prefix declarations. Validated with
        require_prefixes=True before submission.
        """
        validate(sparql, require_prefixes=True)
        response = requests.post(
            self._sparql_url,
            data={"update": sparql},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout,
        )
        response.raise_for_status()

    def count_triples(self, named_graph: Optional[str] = None) -> int:
        """Return the total triple count, optionally scoped to a named graph."""
        if named_graph:
            q = f"SELECT (COUNT(*) AS ?n) FROM <{named_graph}> WHERE {{ ?s ?p ?o }}"
        else:
            q = "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"
        rows = self.query(q)
        return int(rows[0]["n"]) if rows else 0


class MockNeptuneClient:
    """In-memory Neptune stub for unit tests and CI.

    Backed by an rdflib Graph. Accepts the same interface as NeptuneClient
    so notebooks and tests can swap clients without code changes.

    Component class: DETERMINISTIC.
    """

    def __init__(self) -> None:
        from rdflib import ConjunctiveGraph
        self._graph = ConjunctiveGraph()

    def load_turtle(self, ttl: str) -> None:
        """Load a Turtle string into the in-memory graph."""
        self._graph.parse(data=ttl, format="turtle")

    def query(self, sparql: str, named_graph: Optional[str] = None) -> List[Dict[str, Any]]:
        validate(sparql)
        results = self._graph.query(sparql)
        return [
            {str(var): str(val) if val is not None else None for var, val in zip(results.vars, row)}
            for row in results
        ]

    def update(self, sparql: str) -> None:
        validate(sparql, require_prefixes=False)
        self._graph.update(sparql)

    def count_triples(self, named_graph: Optional[str] = None) -> int:
        return len(self._graph)
