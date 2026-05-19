"""
household-traverser — Returns a 1-hop relationship strip for a household URI.

The simplest agent in Phase 1. Executes a single parameterized SPARQL query
and returns the rows. Writes nothing. Read-only.

Component class: DETERMINISTIC, READ-ONLY.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict

# Add shared modules to path for Workshop 1 helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import validate, AtlasSPARQLError

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-bsa-analyst",
    "atlas-ontology-steward",
]

# The 1-hop traversal query template
TRAVERSAL_QUERY = """
SELECT ?uri ?type ?label ?relationship WHERE {{
    <{household_uri}> ?relationship ?uri .
    ?uri a ?type .
    OPTIONAL {{ ?uri rdfs:label ?label }}
}}
"""


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for household-traverser."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Input validation
        household_uri = event.get("household_uri")
        persona_claim = event.get("persona_claim")

        if not household_uri or not isinstance(household_uri, str):
            return _build_response(invocation_id, start_time, "query_error", [],
                                   error_msg="household_uri is required")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _build_response(invocation_id, start_time, "query_error", [],
                                   error_msg=f"persona_claim must be one of: {VALID_PERSONAS}")

        # Build and validate SPARQL
        sparql = TRAVERSAL_QUERY.format(household_uri=household_uri)
        try:
            validate(sparql)
        except AtlasSPARQLError as exc:
            return _build_response(invocation_id, start_time, "query_error", [],
                                   error_msg=f"SPARQL validation failed: {exc}")

        # Execute via atlas-sparql-mcp
        try:
            rows = _invoke_sparql_mcp(sparql, persona_claim)
        except Exception as exc:
            return _build_response(invocation_id, start_time, "query_error", [],
                                   error_msg=f"SPARQL execution failed: {exc}")

        # Parse results into nodes
        if not rows:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _emit_log(invocation_id, persona_claim, execution_time_ms, "not_found", "traverse")
            return {
                "status": "not_found",
                "nodes": [],
                "invocation_id": invocation_id,
                "execution_time_ms": execution_time_ms,
            }

        nodes = [
            {
                "uri": row.get("uri", ""),
                "type": row.get("type", ""),
                "label": row.get("label", ""),
                "relationship": row.get("relationship", ""),
            }
            for row in rows
        ]

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "traverse")

        return {
            "status": "success",
            "nodes": nodes,
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _build_response(invocation_id, start_time, "query_error", [],
                               error_msg=str(exc))


def _invoke_sparql_mcp(sparql: str, persona_claim: str) -> list:
    """Invoke atlas-sparql-mcp for a read query."""
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=SPARQL_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "query",
            "sparql": sparql,
            "persona_claim": persona_claim,
            "graph_tier": "slgd",
        }),
    )
    result = json.loads(response["Payload"].read())
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "SPARQL MCP returned error"))
    return result.get("rows", [])


def _build_response(invocation_id: str, start_time: float, status: str, nodes: list, error_msg: str = "") -> Dict[str, Any]:
    """Build a structured response conforming to output_schema."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "traverse")
    resp = {
        "status": status,
        "nodes": nodes,
        "invocation_id": invocation_id,
        "execution_time_ms": execution_time_ms,
    }
    if error_msg:
        resp["error_message"] = error_msg
    return resp


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "household-traverser",
    }))
