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
import time
import uuid
from typing import Any, Dict, List

from atlas_sparql import validate, AtlasSPARQLError, prefixed, safe_uri

import boto3
import yaml

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

# Cached signal definitions (loaded once per cold start from S3 or fallback dict).
_signal_definitions: dict | None = None


def _load_signal_definitions() -> dict:
    """Load signal query definitions from S3 (SIGNAL_QUERIES_S3_URI) or embedded fallback.

    S3 format: wealth-signals.yaml with a top-level `signals` list. Only entries
    with `enabled: true` are loaded. Falls back to PHASE_1_SIGNALS if S3 is
    unset or unreachable, so unit tests and offline dev remain green.
    """
    global _signal_definitions
    if _signal_definitions is not None:
        return _signal_definitions

    if SIGNAL_QUERIES_S3_URI:
        try:
            parts = SIGNAL_QUERIES_S3_URI.replace("s3://", "").split("/", 1)
            bucket, key = parts[0], parts[1]
            s3 = boto3.client("s3")
            response = s3.get_object(Bucket=bucket, Key=key)
            data = yaml.safe_load(response["Body"].read().decode("utf-8"))
            _signal_definitions = {
                entry["signal_type"]: {
                    "construct_sparql": entry["construct_sparql"],
                    "shape_uri": entry["shape_uri"],
                    "strength": entry["strength"],
                }
                for entry in data.get("signals", [])
                if entry.get("enabled", False)
            }
            logger.info(json.dumps({
                "event": "signal_definitions_loaded",
                "source": "s3",
                "count": len(_signal_definitions),
            }))
            return _signal_definitions
        except Exception as exc:
            logger.warning(json.dumps({
                "event": "signal_definitions_s3_fallback",
                "reason": str(exc),
            }))

    # Embedded fallback — keeps tests green when SIGNAL_QUERIES_S3_URI is unset.
    _signal_definitions = PHASE_1_SIGNALS
    return _signal_definitions


# Phase 1 signal types and their CONSTRUCT queries.
#
# All three types use the atlas-part-2: namespace — these are WS2-derived signals,
# not WS1's LargeDepositPattern / HouseholdAggregationSignal. The agent derives them
# per-customer on demand; WS1 derives its signals batch-style against the whole corpus.
#
# Predicate fix: WS1 uses account → hasTransaction → txn (account is subject).
# The original code had txn → inAccount → acct (reversed). Fixed to match the
# actual promoted triple direction: ?acct atlas:hasTransaction ?txn.
#
# This dict is the embedded fallback used when SIGNAL_QUERIES_S3_URI is unset.
PHASE_1_SIGNALS = {
    "atlas-part-2:LargeInboundWireSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas-part-2:LargeInboundWireSignal ;
                    atlas:aboutCustomer <{target_uri}> ;
                    atlas:signalStrength "strong" ;
                    atlas:evidencedBy ?txn ;
                    prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
            }} WHERE {{
                <{target_uri}> a atlas:Customer ;
                    atlas:hasAccount ?acct .
                ?acct atlas:hasTransaction ?txn .
                ?txn atlas:amountUSD ?amount ;
                     atlas:transactionType "DEPOSIT"^^xsd:string .
                FILTER(?amount > 500000)
                BIND(IRI(CONCAT("urn:signal/wire-", STRUUID())) AS ?signal)
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "strong",
    },
    "atlas-part-2:SegmentShiftSignal": {
        "construct_sparql": """
            PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
            PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
            PREFIX prov: <http://www.w3.org/ns/prov#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            CONSTRUCT {{
                ?signal a atlas:WealthSignal ;
                    atlas:hasSignalType atlas-part-2:SegmentShiftSignal ;
                    atlas:aboutCustomer <{target_uri}> ;
                    atlas:signalStrength "moderate" ;
                    prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
            }} WHERE {{
                <{target_uri}> a atlas:Customer ;
                    atlas:hasAccount ?acct .
                ?acct atlas:hasTransaction ?txn .
                ?txn atlas:amountUSD ?amount .
                FILTER(?amount > 250000)
                BIND(IRI(CONCAT("urn:signal/shift-", STRUUID())) AS ?signal)
            }}
        """,
        "shape_uri": "atlas:WealthSignalTypeShape",
        "strength": "moderate",
    },
    # TODO(ws1-extension): NoAdvisorCoverageSignal is a semantically valid and demo-useful
    # signal (customer with investable assets but no active wealth advisor = referral target),
    # but WS1 never derives it. For the capstone, this type is EXCLUDED from the default run
    # so the UI renders signals that actually exist in the substrate. Implementing the
    # WS1-side derivation is a separate pass (see docs/ws2-comprehension.md).
    #
    # The correct coverage check uses MINUS rather than nested FILTER NOT EXISTS to avoid
    # Neptune's false-negative on FILTER NOT EXISTS { ... FILTER NOT EXISTS { ... } }.
    # Leaving the implementation commented so the fix is visible when this is re-enabled:
    #
    # "atlas-part-2:NoAdvisorCoverageSignal": {
    #     "construct_sparql": """
    #         PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    #         PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
    #         PREFIX prov: <http://www.w3.org/ns/prov#>
    #         CONSTRUCT {{
    #             ?signal a atlas:WealthSignal ;
    #                 atlas:hasSignalType atlas-part-2:NoAdvisorCoverageSignal ;
    #                 atlas:aboutCustomer <{target_uri}> ;
    #                 atlas:signalStrength "gap" ;
    #                 prov:wasGeneratedBy <urn:atlas:wealth-signal-detector> .
    #         }} WHERE {{
    #             <{target_uri}> a atlas:Customer .
    #             MINUS {{
    #                 <{target_uri}> atlas:hasAdvisor ?rel .
    #                 ?rel a atlas:AdvisoryRelationship .
    #                 OPTIONAL {{ ?rel atlas:coverageEndDate ?end }}
    #                 FILTER(!bound(?end))
    #             }}
    #             BIND(IRI(CONCAT("urn:signal/gap-", STRUUID())) AS ?signal)
    #         }}
    #     """,
    #     "shape_uri": "atlas:WealthSignalTypeShape",
    #     "strength": "gap",
    # },
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
        # Validate URI before interpolation into SPARQL templates
        target_uri = safe_uri(target_uri)

        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "validation_failed",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Determine which signals to detect (S3-loaded or embedded fallback)
        all_signals = _load_signal_definitions()
        if signal_types:
            signals_to_run = {k: v for k, v in all_signals.items() if k in signal_types}
        else:
            signals_to_run = all_signals

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
    agentcore_client = boto3.client("bedrock-agentcore")
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=SPARQL_MCP_ARN,
        payload=json.dumps({
            "operation": "construct_and_validate",
            "construct_sparql": sparql,
            "shape_uri": shape_uri,
            "persona_claim": persona_claim,
        }).encode(),
        contentType="application/json",
    )
    result = json.loads(response["response"].read())
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
