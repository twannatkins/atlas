"""
write-routing-decision — Step Functions sub-Lambda #3.

Writes the atlas:RoutingDecision to the SLGD with full PROV-O attribution.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

from atlas_sparql import prefixed

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Write the routing decision to the SLGD."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    household_uri = event.get("household_uri", "")
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    originating_banker_id = event.get("originating_banker_id", "")
    approved_rationale = event.get("approved_rationale", "")
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    routing_decision_uri = f"atlas:routing/{invocation_id}"

    # Build INSERT with PROV-O attribution
    insert_sparql = f"""
    PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        <{routing_decision_uri}> a atlas:RoutingDecision ;
            atlas:selectedRoute "route_to_advisor" ;
            atlas:targetAdvisor <{selected_advisor_uri}> ;
            atlas:aboutHousehold <{household_uri}> ;
            atlas:approvedRationale "{_escape_sparql(approved_rationale)}" ;
            prov:wasGeneratedBy <urn:atlas:referral-orchestrator> ;
            prov:wasAttributedTo <{originating_banker_id}> ;
            prov:generatedAtTime "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"^^xsd:dateTime .
    }}
    """

    try:
        agentcore_client = boto3.client("bedrock-agentcore")
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SPARQL_MCP_ARN,
            payload=json.dumps({
                "operation": "update",
                "sparql": insert_sparql,
                "persona_claim": persona_claim,
            }).encode(),
            contentType="application/json",
        )
        result = json.loads(response["response"].read())
        if result.get("status") == "error":
            return {**event, "status": "workflow_error", "error": result.get("message", "Write failed")}
    except Exception as exc:
        return {**event, "status": "workflow_error", "error": str(exc)}

    return {**event, "status": "decision_written", "routing_decision_uri": routing_decision_uri}


def _escape_sparql(text: str) -> str:
    """Escape special characters for SPARQL string literals."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
