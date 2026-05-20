"""
referral-orchestrator — Orchestrates the state-changing referral routing
workflow via Step Functions.

Entry point Lambda that starts the Step Functions execution. The state
machine coordinates five sub-Lambdas:
  1. select_advisor — queries SLGD for eligible advisors
  2. validate_routing — confirms routing policy compliance via SHACL
  3. write_routing_decision — writes atlas:RoutingDecision to SLGD
  4. notify_advisor — sends notification event
  5. audit_write — writes atlas:AuditRecord with PROV-O attribution

Component class: WORKFLOW — state-changing, fully audited.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
SHACL_MCP_ARN = os.environ.get("SHACL_MCP_ARN", "")

VALID_PERSONAS = ["atlas-consumer-banker"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point — starts the Step Functions execution."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Input validation
        household_uri = event.get("household_uri")
        signal_uris = event.get("signal_uris")
        approved_rationale = event.get("approved_rationale")
        originating_banker_id = event.get("originating_banker_id")
        persona_claim = event.get("persona_claim")

        if not household_uri or not isinstance(household_uri, str):
            return _error_response(invocation_id, start_time, "workflow_error",
                                   "household_uri is required")
        if not signal_uris or not isinstance(signal_uris, list):
            return _error_response(invocation_id, start_time, "workflow_error",
                                   "signal_uris is required and must be an array")
        if not approved_rationale or not isinstance(approved_rationale, str):
            return _error_response(invocation_id, start_time, "workflow_error",
                                   "approved_rationale is required (human must approve before routing)")
        if not originating_banker_id or not isinstance(originating_banker_id, str):
            return _error_response(invocation_id, start_time, "workflow_error",
                                   "originating_banker_id is required")
        if persona_claim != "atlas-consumer-banker":
            return _error_response(invocation_id, start_time, "workflow_error",
                                   "Only atlas-consumer-banker can invoke referral-orchestrator")

        # Start Step Functions execution
        sfn_client = boto3.client("stepfunctions")
        execution_input = {
            "household_uri": household_uri,
            "signal_uris": signal_uris,
            "approved_rationale": approved_rationale,
            "originating_banker_id": originating_banker_id,
            "persona_claim": persona_claim,
            "invocation_id": invocation_id,
        }

        try:
            response = sfn_client.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=f"referral-{invocation_id}",
                input=json.dumps(execution_input),
            )
            execution_arn = response["executionArn"]
        except Exception as exc:
            return _error_response(invocation_id, start_time, "workflow_error",
                                   f"Failed to start Step Functions execution: {exc}")

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "routed", "orchestrate")

        return {
            "status": "routed",
            "routing_decision_uri": f"atlas:routing/{invocation_id}",
            "selected_advisor_uri": "",  # Populated by the state machine
            "audit_record_uri": f"atlas:audit/{invocation_id}",
            "execution_arn": execution_arn,
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "workflow_error", str(exc))


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    """Build a structured error response."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "routing_decision_uri": "",
        "selected_advisor_uri": "",
        "audit_record_uri": "",
        "execution_arn": "",
        "error_message": message,
        "invocation_id": invocation_id,
        "execution_time_ms": execution_time_ms,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "referral-orchestrator",
    }))
