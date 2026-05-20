"""
atlas-er-mcp — MCP server wrapping AWS Entity Resolution lookups.

Exposes three operations:
  - lookup: resolve source_system + source_id to canonical URI
  - resolve: submit record attributes to ER and receive MatchID → URI
  - link: record a verified link between source record and canonical URI

Component class: DETERMINISTIC — same input record = same canonical URI
(assuming the ER workflow state hasn't changed).
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
ER_WORKFLOW_NAME = os.environ.get("ER_WORKFLOW_NAME", "")

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-bsa-analyst",
    "atlas-ontology-steward",
    "atlas-auditor",
]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for atlas-er-mcp."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        operation = event.get("operation")
        if operation not in ("lookup", "resolve", "link"):
            return _error_response(
                invocation_id, start_time,
                "invalid_operation",
                f"Unknown operation: {operation}. Must be one of: lookup, resolve, link",
            )

        if operation == "lookup":
            return _handle_lookup(event, invocation_id, start_time)
        elif operation == "resolve":
            return _handle_resolve(event, invocation_id, start_time)
        else:
            return _handle_link(event, invocation_id, start_time)

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "internal_error", str(exc))


def _handle_lookup(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Look up canonical URI from source system and source ID."""
    source_system = event.get("source_system")
    source_id = event.get("source_id")

    if not source_system or not isinstance(source_system, str):
        return _error_response(invocation_id, start_time, "validation_error", "source_system is required")
    if not source_id or not isinstance(source_id, str):
        return _error_response(invocation_id, start_time, "validation_error", "source_id is required")

    try:
        er_client = boto3.client("entityresolution")
        response = er_client.get_match_id(
            workflowName=ER_WORKFLOW_NAME,
            record={
                "source_system": {"valueAsString": source_system},
                "source_id": {"valueAsString": source_id},
            },
        )

        match_id = response.get("matchId", "")
        if not match_id:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _emit_log(invocation_id, "system", execution_time_ms, "no_match", "lookup")
            return {
                "status": "no_match",
                "canonical_uri": "",
                "match_confidence": 0.0,
                "message": f"No match found for {source_system}:{source_id}",
                "execution_time_ms": execution_time_ms,
                "invocation_id": invocation_id,
            }

        # Derive canonical URI from match ID
        canonical_uri = f"atlas:entity/{match_id}"
        match_confidence = response.get("confidenceScore", 1.0)

    except Exception as exc:
        return _error_response(invocation_id, start_time, "er_lookup_error", f"Entity Resolution lookup failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, "success", "lookup")

    return {
        "status": "success",
        "canonical_uri": canonical_uri,
        "match_confidence": match_confidence,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_resolve(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Submit record attributes to ER and receive MatchID → canonical URI."""
    record_attributes = event.get("record_attributes")

    if not record_attributes or not isinstance(record_attributes, dict):
        return _error_response(invocation_id, start_time, "validation_error", "record_attributes is required and must be an object")

    try:
        er_client = boto3.client("entityresolution")
        # Convert attributes to ER record format
        record = {k: {"valueAsString": str(v)} for k, v in record_attributes.items()}

        response = er_client.get_match_id(
            workflowName=ER_WORKFLOW_NAME,
            record=record,
        )

        match_id = response.get("matchId", "")
        if not match_id:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _emit_log(invocation_id, "system", execution_time_ms, "no_match", "resolve")
            return {
                "status": "no_match",
                "match_id": "",
                "canonical_uri": "",
                "message": "No match found for provided attributes",
                "execution_time_ms": execution_time_ms,
                "invocation_id": invocation_id,
            }

        canonical_uri = f"atlas:entity/{match_id}"

    except Exception as exc:
        return _error_response(invocation_id, start_time, "er_resolve_error", f"Entity Resolution resolve failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, "success", "resolve")

    return {
        "status": "success",
        "match_id": match_id,
        "canonical_uri": canonical_uri,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_link(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Record a verified link between a source record URI and canonical URI."""
    source_record_uri = event.get("source_record_uri")
    canonical_uri = event.get("canonical_uri")

    if not source_record_uri or not isinstance(source_record_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "source_record_uri is required")
    if not canonical_uri or not isinstance(canonical_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "canonical_uri is required")

    # In a full deployment, this writes the link to a resolution table or graph.
    # For the workshop, we record the link assertion and return success.
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, "success", "link")

    return {
        "status": "success",
        "link_recorded": True,
        "source_record_uri": source_record_uri,
        "canonical_uri": canonical_uri,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


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
        "service": "atlas-er-mcp",
    }))
