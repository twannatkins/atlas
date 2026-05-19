"""
atlas-fibo-mcp — MCP server for FIBO class introspection and ontology browsing.

Exposes three operations:
  - class_info: label, comment, parent classes, FIBO alignment for a class URI
  - list_classes: list all classes in a namespace
  - subclasses_of: find subclasses of a given class

Delegates SPARQL queries to atlas-sparql-mcp. Does not modify the ontology.

Component class: DETERMINISTIC — read-only introspection.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

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
    "atlas-auditor",
]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for atlas-fibo-mcp."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        operation = event.get("operation")
        if operation not in ("class_info", "list_classes", "subclasses_of"):
            return _error_response(
                invocation_id, start_time,
                "invalid_operation",
                f"Unknown operation: {operation}. Must be one of: class_info, list_classes, subclasses_of",
            )

        if operation == "class_info":
            return _handle_class_info(event, invocation_id, start_time)
        elif operation == "list_classes":
            return _handle_list_classes(event, invocation_id, start_time)
        else:
            return _handle_subclasses_of(event, invocation_id, start_time)

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "internal_error", str(exc))


def _handle_class_info(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Return label, comment, parents, and FIBO alignment for a class URI."""
    class_uri = event.get("class_uri")

    if not class_uri or not isinstance(class_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "class_uri is required")

    # Query for class metadata via atlas-sparql-mcp
    sparql = f"""
    SELECT ?label ?comment ?parent ?alignment WHERE {{
        <{class_uri}> rdfs:label ?label .
        OPTIONAL {{ <{class_uri}> rdfs:comment ?comment }}
        OPTIONAL {{ <{class_uri}> rdfs:subClassOf ?parent }}
        OPTIONAL {{ <{class_uri}> owl:equivalentClass ?alignment }}
    }}
    """

    try:
        rows = _invoke_sparql_mcp(sparql, event.get("persona_claim", "atlas-ontology-steward"))
    except Exception as exc:
        return _error_response(invocation_id, start_time, "sparql_error", f"SPARQL query failed: {exc}")

    # Parse results
    label = rows[0]["label"] if rows and rows[0].get("label") else class_uri.split("#")[-1].split("/")[-1]
    comment = rows[0].get("comment", "") if rows else ""
    parents = list({r["parent"] for r in rows if r.get("parent")})
    fibo_alignment = rows[0].get("alignment", "") if rows else ""

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, event.get("persona_claim", "system"), execution_time_ms, "success", "class_info")

    return {
        "status": "success",
        "label": label,
        "comment": comment,
        "parents": parents,
        "fibo_alignment": fibo_alignment,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_list_classes(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """List all classes in a namespace."""
    namespace_prefix = event.get("namespace_prefix")

    if not namespace_prefix or not isinstance(namespace_prefix, str):
        return _error_response(invocation_id, start_time, "validation_error", "namespace_prefix is required")

    sparql = f"""
    SELECT ?class ?label WHERE {{
        ?class a owl:Class .
        FILTER(STRSTARTS(STR(?class), STR({namespace_prefix}:)))
        OPTIONAL {{ ?class rdfs:label ?label }}
    }}
    """

    try:
        rows = _invoke_sparql_mcp(sparql, event.get("persona_claim", "atlas-ontology-steward"))
    except Exception as exc:
        return _error_response(invocation_id, start_time, "sparql_error", f"SPARQL query failed: {exc}")

    classes = [{"uri": r["class"], "label": r.get("label", "")} for r in rows]

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, event.get("persona_claim", "system"), execution_time_ms, "success", "list_classes")

    return {
        "status": "success",
        "classes": classes,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_subclasses_of(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Find subclasses of a given class."""
    class_uri = event.get("class_uri")

    if not class_uri or not isinstance(class_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "class_uri is required")

    sparql = f"""
    SELECT ?subclass ?label WHERE {{
        ?subclass rdfs:subClassOf <{class_uri}> .
        OPTIONAL {{ ?subclass rdfs:label ?label }}
    }}
    """

    try:
        rows = _invoke_sparql_mcp(sparql, event.get("persona_claim", "atlas-ontology-steward"))
    except Exception as exc:
        return _error_response(invocation_id, start_time, "sparql_error", f"SPARQL query failed: {exc}")

    subclasses = [{"uri": r["subclass"], "label": r.get("label", "")} for r in rows]

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, event.get("persona_claim", "system"), execution_time_ms, "success", "subclasses_of")

    return {
        "status": "success",
        "subclasses": subclasses,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


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


def _error_response(invocation_id: str, start_time: float, error_type: str, message: str) -> Dict[str, Any]:
    """Build a structured error response."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, error_type, "error")
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
        "service": "atlas-fibo-mcp",
    }))
