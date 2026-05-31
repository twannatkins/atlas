"""
atlas_neptune — thin Neptune SPARQL endpoint client with IAM auth.

Wraps the Neptune SPARQL HTTP endpoint. All queries pass through
atlas_sparql.validate() before submission. Requests are authenticated
using SigV4 signing via the boto3 credential chain — the caller's IAM
role must have neptune-db:ReadDataViaQuery and/or
neptune-db:WriteDataViaQuery permissions on the cluster resource.

Component class: DETERMINISTIC — given the same endpoint state and
query, the client always submits the same wire request and returns
the same parsed response.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

from atlas_sparql import validate, AtlasSPARQLError


class NeptuneClient:
    """SPARQL client for an Amazon Neptune endpoint with IAM auth.

    Authenticates requests using SigV4 signing. The IAM principal
    (Lambda execution role, SageMaker execution role, etc.) must have
    the neptune-db:* permissions granted by the NeptuneIamAuthPolicy
    managed policy exported from the atlas-neptune-twotier stack.

    Parameters
    ----------
    endpoint:
        Neptune cluster endpoint hostname, e.g.
        ``my-cluster.cluster-xxxx.us-east-1.neptune.amazonaws.com``.
        If omitted, reads from the environment variable
        ``ATLAS_NEPTUNE_ENDPOINT``.
    port:
        Neptune SPARQL port. Default 8182.
    region:
        AWS region for SigV4 signing. Default reads from
        ``AWS_REGION`` or ``AWS_DEFAULT_REGION`` environment variable.
    timeout:
        Request timeout in seconds. Default 30.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        port: int = 8182,
        region: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        host = endpoint or os.environ.get("ATLAS_NEPTUNE_ENDPOINT")
        if not host:
            raise ValueError(
                "Neptune endpoint not specified. Pass 'endpoint=' or set "
                "the ATLAS_NEPTUNE_ENDPOINT environment variable."
            )
        self._sparql_url = f"https://{host}:{port}/sparql"
        self._timeout = timeout
        self._region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._session = boto3.Session()

    def _sign_request(self, method: str, url: str, headers: Dict[str, str], data: Optional[str] = None) -> Dict[str, str]:
        """Sign an HTTP request with SigV4 for Neptune IAM auth."""
        credentials = self._session.get_credentials().get_frozen_credentials()
        request = AWSRequest(method=method, url=url, headers=headers, data=data or "")
        SigV4Auth(credentials, "neptune-db", self._region).add_auth(request)
        return dict(request.headers)

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

        # Use POST with query in body — same pattern as the working signed helpers.
        # GET with SigV4 requires exact Host header preservation which requests.get()
        # doesn't guarantee; POST is more reliable and Neptune supports both.
        url = self._sparql_url
        data = f"query={requests.utils.quote(validated)}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
            "Host": url.split("/")[2],
        }
        aw = AWSRequest(method="POST", url=url, headers=headers, data=data)
        SigV4Auth(self._session.get_credentials().get_frozen_credentials(), "neptune-db", self._region).add_auth(aw)
        prep = requests.Request(method="POST", url=url, headers=dict(aw.headers), data=data).prepare()
        sess = requests.Session()
        response = sess.send(prep, timeout=self._timeout, verify=True)

        response.raise_for_status()
        result = response.json()
        # Neptune SPARQL JSON format: {"head": {"vars": [...]}, "results": {"bindings": [...]}}
        vars_ = result["head"]["vars"]
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
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = f"update={requests.utils.quote(sparql)}"
        signed_headers = self._sign_request("POST", self._sparql_url, headers, body)

        response = requests.post(
            self._sparql_url,
            data=body,
            headers=signed_headers,
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
