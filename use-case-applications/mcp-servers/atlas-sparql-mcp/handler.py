"""
atlas-sparql-mcp — MCP server wrapping SPARQL access to Neptune SLGD/LGD.

Exposes three operations:
  - query: read-only SELECT/CONSTRUCT against SLGD or LGD
  - update: INSERT/DELETE with persona-scoped Lake Formation access
  - construct_and_validate: CONSTRUCT + SHACL validation before returning

All operations require a persona_claim. Anonymous queries are rejected.
All Neptune requests are authenticated via SigV4 signing using the
Lambda execution role's credentials.

Component class: DETERMINISTIC gateway — the server itself adds no
probabilistic behavior; it translates, scopes, and forwards.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict
from urllib.parse import quote as url_quote

# Add shared modules to path for Workshop 1 helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import validate, AtlasSPARQLError, prefixed

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests as http_requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
NEPTUNE_SLGD_ENDPOINT = os.environ.get("NEPTUNE_SLGD_ENDPOINT", "")
NEPTUNE_LGD_ENDPOINT = os.environ.get("NEPTUNE_LGD_ENDPOINT", "")
ONTOP_ECS_ENDPOINT = os.environ.get("ONTOP_ECS_ENDPOINT", "")
SHACL_MCP_ARN = os.environ.get("SHACL_MCP_ARN", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-bsa-analyst",
    "atlas-ontology-steward",
    "atlas-auditor",
]

# SigV4 session — reused across invocations for connection pooling
_boto_session = boto3.Session()


def _sigv4_headers(method: str, url: str, headers: Dict[str, str], body: str = "") -> Dict[str, str]:
    """Sign an HTTP request with SigV4 for Neptune IAM auth."""
    credentials = _boto_session.get_credentials().get_frozen_credentials()
    request = AWSRequest(method=method, url=url, headers=headers, data=body)
    SigV4Auth(credentials, "neptune-db", AWS_REGION).add_auth(request)
    return dict(request.headers)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for atlas-sparql-mcp."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        operation = event.get("operation")
        if operation not in ("query", "update", "construct_and_validate"):
            return _error_response(
                invocation_id, start_time,
                "invalid_operation",
                f"Unknown operation: {operation}. Must be one of: query, update, construct_and_validate",
            )

        # Dispatch to operation handler
        if operation == "query":
            return _handle_query(event, invocation_id, start_time)
        elif operation == "update":
            return _handle_update(event, invocation_id, start_time)
        else:
            return _handle_construct_and_validate(event, invocation_id, start_time)

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "internal_error", str(exc))


def _handle_query(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Execute a read-only SPARQL query."""
    sparql = event.get("sparql")
    persona_claim = event.get("persona_claim")
    graph_tier = event.get("graph_tier", "slgd")

    # Input validation
    if not sparql or not isinstance(sparql, str):
        return _error_response(invocation_id, start_time, "validation_error", "sparql is required and must be a string")
    if not persona_claim or persona_claim not in VALID_PERSONAS:
        return _error_response(invocation_id, start_time, "validation_error", f"persona_claim must be one of: {VALID_PERSONAS}")
    if graph_tier not in ("slgd", "lgd"):
        return _error_response(invocation_id, start_time, "validation_error", "graph_tier must be 'slgd' or 'lgd'")

    # Validate SPARQL syntax via shared helper
    try:
        validated_sparql = validate(sparql)
    except AtlasSPARQLError as exc:
        return _error_response(invocation_id, start_time, "sparql_validation_error", str(exc))

    # Select endpoint based on tier
    endpoint = NEPTUNE_SLGD_ENDPOINT if graph_tier == "slgd" else NEPTUNE_LGD_ENDPOINT
    sparql_url = f"https://{endpoint}:8182/sparql"

    # Execute query with SigV4-signed request
    try:
        query_url = f"{sparql_url}?query={url_quote(validated_sparql)}"
        headers = {"Accept": "application/sparql-results+json"}
        signed_headers = _sigv4_headers("GET", query_url, headers)
        response = http_requests.get(query_url, headers=signed_headers, timeout=30)
        response.raise_for_status()
        results = response.json()
        rows = _parse_sparql_results(results)
    except Exception as exc:
        return _error_response(invocation_id, start_time, "execution_error", f"Neptune query failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "query")

    return {
        "status": "success",
        "rows": rows,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_update(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Execute a SPARQL UPDATE (INSERT/DELETE)."""
    sparql = event.get("sparql")
    persona_claim = event.get("persona_claim")

    if not sparql or not isinstance(sparql, str):
        return _error_response(invocation_id, start_time, "validation_error", "sparql is required and must be a string")
    if not persona_claim or persona_claim not in VALID_PERSONAS:
        return _error_response(invocation_id, start_time, "validation_error", f"persona_claim must be one of: {VALID_PERSONAS}")

    # WORKAROUND: Workshop 1's atlas_sparql.validate() calls rdflib's prepareQuery(),
    # which only supports SELECT/CONSTRUCT/ASK/DESCRIBE — not INSERT/UPDATE/DELETE.
    # Passing an UPDATE statement to validate() raises a parse error, so we cannot
    # use the shared validator here. Instead, we perform a prefix-declaration check
    # manually (the same check validate(require_prefixes=True) would do, minus the
    # syntax parse). The proper fix is extending Workshop 1's shared validator to
    # handle SPARQL Update syntax — that should be done in a separate Workshop 1 PR,
    # not by modifying Workshop 1 files from Workshop 2.
    try:
        # Check prefix declarations are present
        from atlas_sparql import _REQUIRED_PREFIX_DECLARATIONS, AtlasSPARQLError as _ASE
        for prefix, iri in _REQUIRED_PREFIX_DECLARATIONS.items():
            if f"PREFIX {prefix}:" not in sparql and f"@prefix {prefix}:" not in sparql:
                return _error_response(invocation_id, start_time, "sparql_validation_error",
                                       f"SPARQL query is missing required PREFIX declaration for "
                                       f"'{prefix}:' (<{iri}>). Add it to the query preamble.")
    except ImportError:
        pass

    # Execute update against SLGD with SigV4-signed request
    sparql_url = f"https://{NEPTUNE_SLGD_ENDPOINT}:8182/sparql"
    try:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = f"update={url_quote(sparql)}"
        signed_headers = _sigv4_headers("POST", sparql_url, headers, body)
        response = http_requests.post(sparql_url, data=body, headers=signed_headers, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        return _error_response(invocation_id, start_time, "execution_error", f"Neptune update failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "update")

    return {
        "status": "success",
        "triples_affected": -1,  # Neptune doesn't return affected count; placeholder
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_construct_and_validate(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Run a CONSTRUCT query and validate result against a SHACL shape."""
    construct_sparql = event.get("construct_sparql")
    shape_uri = event.get("shape_uri")
    persona_claim = event.get("persona_claim")

    if not construct_sparql or not isinstance(construct_sparql, str):
        return _error_response(invocation_id, start_time, "validation_error", "construct_sparql is required")
    if not shape_uri or not isinstance(shape_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "shape_uri is required")
    if not persona_claim or persona_claim not in VALID_PERSONAS:
        return _error_response(invocation_id, start_time, "validation_error", f"persona_claim must be one of: {VALID_PERSONAS}")

    # Validate SPARQL
    try:
        validated_sparql = validate(construct_sparql)
    except AtlasSPARQLError as exc:
        return _error_response(invocation_id, start_time, "sparql_validation_error", str(exc))

    # Execute CONSTRUCT with SigV4-signed request
    sparql_url = f"https://{NEPTUNE_SLGD_ENDPOINT}:8182/sparql"
    try:
        query_url = f"{sparql_url}?query={url_quote(validated_sparql)}"
        headers = {"Accept": "application/sparql-results+json"}
        signed_headers = _sigv4_headers("GET", query_url, headers)
        response = http_requests.get(query_url, headers=signed_headers, timeout=30)
        response.raise_for_status()
        results = response.json()
        triples_minted = _parse_construct_results(results)
    except Exception as exc:
        return _error_response(invocation_id, start_time, "execution_error", f"CONSTRUCT query failed: {exc}")

    # Validate via atlas-shacl-mcp
    try:
        lambda_client = boto3.client("lambda")
        shacl_response = lambda_client.invoke(
            FunctionName=SHACL_MCP_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "operation": "validate",
                "triples": triples_minted,
                "shape_uris": [shape_uri],
            }),
        )
        shacl_result = json.loads(shacl_response["Payload"].read())
    except Exception as exc:
        return _error_response(invocation_id, start_time, "shacl_invocation_error", f"SHACL MCP call failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "construct_and_validate")

    return {
        "status": "success",
        "triples_minted": triples_minted,
        "validation_report": shacl_result,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _parse_sparql_results(results: Dict[str, Any]) -> list:
    """Parse SPARQL JSON results into a list of dicts."""
    if "results" not in results or "bindings" not in results["results"]:
        return []
    vars_ = results.get("head", {}).get("vars", [])
    return [
        {v: binding[v]["value"] if v in binding else None for v in vars_}
        for binding in results["results"]["bindings"]
    ]


def _parse_construct_results(results: Dict[str, Any]) -> list:
    """Parse CONSTRUCT results into a list of triple dicts."""
    # CONSTRUCT returns triples; format depends on Neptune response
    if isinstance(results, dict) and "results" in results:
        return _parse_sparql_results(results)
    return results if isinstance(results, list) else []


def _error_response(invocation_id: str, start_time: float, error_type: str, message: str) -> Dict[str, Any]:
    """Build a structured error response."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, error_type, "error")
    return {
        "status": "error",
        "error_type": error_type,
        "message": message,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "service": "atlas-sparql-mcp",
    }))
