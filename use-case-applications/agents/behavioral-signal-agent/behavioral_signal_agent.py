"""
behavioral-signal-agent — Detects behavioral signals (EngagementDecay,
NetworkInfluence) by querying LGD-derived sessions and cross-LOB traversals.

Phase 2 only. Extends the deterministic signal-detection pattern from
wealth-signal-detector with new signal types backed by LGD-derived data.

Component class: DETERMINISTIC, SHACL-DRIVEN.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List

from atlas_sparql import validate, AtlasSPARQLError, safe_uri

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
SHACL_MCP_ARN = os.environ.get("SHACL_MCP_ARN", "")

VALID_PERSONAS = ["atlas-wealth-advisor"]

# Phase 2 behavioral signal CONSTRUCT queries
PHASE_2_SIGNALS = {
    "atlas-part-2:EngagementDecaySignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas-part-2:EngagementDecaySignal ;
                    atlas:aboutCustomer <{customer_uri}> ;
                    atlas:signalStrength "moderate" ;
                    prov:wasGeneratedBy <urn:atlas:behavioral-signal-agent> .
            }} WHERE {{
                <{customer_uri}> a atlas:Customer .
                ?session a atlas-part-2:Session ;
                    atlas-part-2:forCustomer <{customer_uri}> ;
                    atlas-part-2:sessionDate ?date .
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "moderate",
        "graph_tier": "lgd",
    },
    "atlas-part-2:NetworkInfluenceSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas-part-2:NetworkInfluenceSignal ;
                    atlas:aboutCustomer <{customer_uri}> ;
                    atlas:signalStrength "moderate" ;
                    prov:wasGeneratedBy <urn:atlas:behavioral-signal-agent> .
            }} WHERE {{
                <{customer_uri}> a atlas:Customer ;
                    atlas:memberOf ?household .
                ?contact a atlas-part-2:NetworkContact ;
                    atlas-part-2:involvesHousehold ?household ;
                    atlas-part-2:crossLOB true .
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "moderate",
        "graph_tier": "slgd",
    },
}


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for behavioral-signal-agent."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        customer_uri = event.get("customer_uri")
        persona_claim = event.get("persona_claim")

        if not customer_uri or not isinstance(customer_uri, str):
            return _error_response(invocation_id, start_time, "validation_failed",
                                   "customer_uri is required")
        # Validate URI before interpolation into SPARQL templates
        customer_uri = safe_uri(customer_uri)

        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "validation_failed",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        signals_minted: List[Dict[str, Any]] = []

        for signal_type, config in PHASE_2_SIGNALS.items():
            sparql = config["construct_sparql"].format(customer_uri=customer_uri)
            shape_uri = config["shape_uri"]

            try:
                result = _invoke_construct_and_validate(sparql, shape_uri, persona_claim)
                triples = result.get("triples_minted", [])
                if triples:
                    signals_minted.append({
                        "signal_uri": f"atlas:signal/{uuid.uuid4().hex[:12]}",
                        "signal_type": signal_type,
                        "strength": config["strength"],
                    })
            except Exception as exc:
                logger.warning(json.dumps({
                    "invocation_id": invocation_id,
                    "signal_type": signal_type,
                    "error": str(exc),
                }))

        status = "success" if signals_minted else "no_signals_detected"
        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, status, "detect")

        return {
            "status": status,
            "signals_minted": signals_minted,
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return _error_response(invocation_id, start_time, "validation_failed", str(exc))


def _invoke_construct_and_validate(sparql: str, shape_uri: str, persona_claim: str) -> dict:
    """Invoke atlas-sparql-mcp construct_and_validate."""
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
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "signals_minted": [],
        "error_message": message,
        "invocation_id": invocation_id,
        "execution_time_ms": execution_time_ms,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "behavioral-signal-agent",
    }))
