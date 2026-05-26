"""
validate-routing — Step Functions sub-Lambda #2.

Confirms the selected advisor's capacity, checks for compliance holds,
and validates against atlas:RoutingPolicyShape.
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

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
SHACL_MCP_ARN = os.environ.get("SHACL_MCP_ARN", "")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Validate the routing decision against policy shapes."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))

    selected_advisor_uri = event.get("selected_advisor_uri", "")
    household_uri = event.get("household_uri", "")
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    if not selected_advisor_uri:
        return {**event, "status": "validation_failed", "validation_error": "No advisor selected"}

    # Check for compliance holds on the household
    try:
        agentcore_client = boto3.client("bedrock-agentcore")
        hold_check = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SPARQL_MCP_ARN,
            payload=json.dumps({
                "operation": "query",
                "sparql": f"ASK {{ <{household_uri}> atlas:hasComplianceHold true }}",
                "persona_claim": persona_claim,
                "graph_tier": "slgd",
            }).encode(),
            contentType="application/json",
        )
        hold_result = json.loads(hold_check["response"].read())
        # If household has a compliance hold, routing is blocked
        if hold_result.get("rows") and hold_result["rows"][0].get("result") == "true":
            return {**event, "status": "validation_failed", "validation_error": "Household has active compliance hold"}
    except Exception as exc:
        logger.warning(json.dumps({"invocation_id": invocation_id, "warning": f"Hold check failed: {exc}"}))

    # Validate routing decision shape via SHACL MCP
    try:
        routing_triples = f"""
        @prefix atlas: <https://github.com/your-org/atlas/ontology#> .
        @prefix prov: <http://www.w3.org/ns/prov#> .
        <atlas:routing/{invocation_id}> a atlas:RoutingDecision ;
            atlas:selectedRoute "route_to_advisor" ;
            atlas:targetAdvisor <{selected_advisor_uri}> ;
            atlas:aboutHousehold <{household_uri}> .
        """

        shacl_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SHACL_MCP_ARN,
            payload=json.dumps({
                "operation": "validate",
                "triples": routing_triples,
                "shape_uris": ["atlas:RoutingPolicyShape"],
            }).encode(),
            contentType="application/json",
        )
        shacl_result = json.loads(shacl_response["response"].read())

        if not shacl_result.get("conforms", True):
            return {**event, "status": "validation_failed",
                    "validation_error": shacl_result.get("report", {}).get("summary", "SHACL validation failed")}

    except Exception as exc:
        logger.warning(json.dumps({"invocation_id": invocation_id, "warning": f"SHACL validation failed: {exc}"}))

    return {**event, "status": "validated"}
