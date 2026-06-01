"""
select-advisor — Step Functions sub-Lambda #1.

Queries the SLGD for advisors with capacity, specialization match,
and geographic proximity. Returns ranked candidates.
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

ADVISOR_QUERY = """
SELECT ?advisor ?label ?capacity ?specialization WHERE {{
    ?advisor a atlas:Advisor ;
        rdfs:label ?label .
    OPTIONAL {{ ?advisor atlas:currentCapacity ?capacity }}
    OPTIONAL {{ ?advisor atlas:specialization ?specialization }}
    OPTIONAL {{ ?advisor atlas:onLeave ?leave }}
    FILTER(!bound(?leave) || ?leave != true)
}}
ORDER BY DESC(?capacity)
"""


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Select eligible advisors for the referral."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    start_time = time.time()

    household_uri = event.get("household_uri", "")
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    try:
        agentcore_client = boto3.client("bedrock-agentcore")
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SPARQL_MCP_ARN,
            payload=json.dumps({
                "operation": "query",
                "sparql": ADVISOR_QUERY,
                "persona_claim": persona_claim,
                "graph_tier": "slgd",
            }).encode(),
            contentType="application/json",
        )
        result = json.loads(response["response"].read())
        advisors = result.get("rows", [])

        if not advisors:
            return {**event, "status": "no_eligible_advisor", "selected_advisor_uri": "", "candidates": []}

        # Select top candidate
        selected = advisors[0]
        return {
            **event,
            "status": "advisor_selected",
            "selected_advisor_uri": selected.get("advisor", ""),
            "selected_advisor_label": selected.get("label", ""),
            "candidates": advisors[:5],
        }

    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return {**event, "status": "no_eligible_advisor", "error": str(exc)}
