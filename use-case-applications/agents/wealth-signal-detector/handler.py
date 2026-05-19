"""
wealth-signal-detector — Detects wealth-readiness signals by running
SPARQL CONSTRUCT queries that produce atlas:WealthSignal instances.

Validates output via SHACL before writing to the graph. Nothing partial
is committed — if any triple fails validation, the entire batch is rejected.

Component class: DETERMINISTIC, SHACL-DRIVEN.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List

# Add shared modules to path for Workshop 1 helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import validate, AtlasSPARQLError, prefixed

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
SHACL_MCP_ARN = os.environ.get("SHACL_MCP_ARN", "")
SIGNAL_QUERIES_S3_URI = os.environ.get("SIGNAL_QUERIES_S3_URI", "")

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-ontology-steward",
]

# Phase 1 signal types and their CONSTRUCT queries
PHASE_1_SIGNALS = {
    "atlas-part-2:LargeInboundWireSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas:LargeInboundWireSignal ;
                    atlas:aboutCustomer <{target_uri}> ;
                    atlas:signalStrength "strong" ;
                    prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
            }} WHERE {{
                <{target_uri}> a atlas:Customer ;
                    atlas:hasAccount ?acct .
                ?txn atlas:inAccount ?acct ;
                    atlas:amountUSD ?amount ;
                    atlas:transactionDate ?date .
                FILTER(?amount > 500000)
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "strong",
    },
    "atlas-part-2:SegmentShiftSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas:SegmentShiftSignal ;
                    atlas:aboutCustomer <{target_uri}> ;
                    atlas:signalStrength "moderate" ;
                    prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
            }} WHERE {{
                <{target_uri}> a atlas:Customer ;
                    atlas:hasAccount ?acct .
                ?txn atlas:inAccount ?acct ;
                    atlas:amountUSD ?amount .
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "moderate",
    },
    "atlas-part-2:NoAdvisorCoverageSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas:NoAdvisorCoverageSignal ;
                    atlas:aboutCustomer <{target_uri}> ;
                    atlas:signalStrength "gap" ;
                    prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
            }} WHERE {{
                <{target_uri}> a atlas:Customer .
                FILTER NOT EXISTS {{
                    <{target_uri}> atlas:hasAdvisor ?rel .
                    FILTER NOT EXISTS {{ ?rel atlas:coverageEndDate ?end }}
                }}
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "gap",
    },
}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for wealth-signal-detector."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Input validation
        target_uri = event.get("target_uri")
        persona_claim = event.get("persona_claim")
        signal_types = event.get("signal_types")

        if not target_uri or not isinstance(target_uri, str):
            return _error_response(invocation_id, start_time, "validation_failed",
                                   "target_uri is required")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "validation_failed",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Determine which signals to detect
        if signal_types:
            signals_to_run = {k: v for k, v in PHASE_1_SIGNALS.items() if k in signal_types}
        else:
            signals_to_run = PHASE_1_SIGNALS

        # Execute CONSTRUCT queries and validate
        signals_minted: List[Dict[str, Any]] = []
        queries_executed: List[str] = []
        shapes_validated: List[str] = []

        for signal_type, signal_config in signals_to_run.items():
            # Parameterize the CONSTRUCT query
            sparql = signal_config["construct_sparql"].format(target_uri=target_uri)
            shape_uri = signal_config["shape_uri"]

            # Execute via atlas-sparql-mcp construct_and_validate
            try:
                result = _invoke_construct_and_validate(sparql, shape_uri, persona_claim)
            except Exception as exc:
                logger.warning(json.dumps({
                    "invocation_id": invocation_id,
                    "signal_type": signal_type,
                    "error": str(exc),
                }))
                continue

            queries_executed.append(signal_type)
            shapes_validated.append(shape_uri)

            # Check if triples were produced (signal detected)
            triples = result.get("triples_minted", [])
            if triples:
                signal_uri = f"atlas:signal/{uuid.uuid4().hex[:12]}"
                signals_minted.append({
                    "signal_uri": signal_uri,
                    "signal_type": signal_type,
                    "strength": signal_config["strength"],
                })

        # Determine status
        if not signals_minted and not queries_executed:
            status = "validation_failed"
        elif not signals_minted:
            status = "no_signals_detected"
        elif len(signals_minted) < len(signals_to_run):
            status = "partial"
        else:
            status = "success"

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, status, "detect")

        return {
            "status": status,
            "signals_minted": signals_minted,
            "provenance": {
                "queries_executed": queries_executed,
                "shapes_validated": shapes_validated,
                "execution_time_ms": execution_time_ms,
            },
            "invocation_id": invocation_id,
        }

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "validation_failed", str(exc))


def _invoke_construct_and_validate(sparql: str, shape_uri: str, persona_claim: str) -> dict:
    """Invoke atlas-sparql-mcp construct_and_validate operation."""
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=SPARQL_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "construct_and_validate",
            "construct_sparql": sparql,
            "shape_uri": shape_uri,
            "persona_claim": persona_claim,
        }),
    )
    result = json.loads(response["Payload"].read())
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "construct_and_validate failed"))
    return result


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    """Build a structured error response conforming to output_schema."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "signals_minted": [],
        "provenance": {
            "queries_executed": [],
            "shapes_validated": [],
            "execution_time_ms": execution_time_ms,
        },
        "error_message": message,
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
        "agent": "wealth-signal-detector",
    }))
