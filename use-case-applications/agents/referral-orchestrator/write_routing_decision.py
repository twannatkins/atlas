"""
write-routing-decision — Step Functions sub-Lambda #3.

Writes atlas:RoutingDecision to SLGD with PROV-O attribution.
Calls Neptune directly (SigV4 POST UPDATE).

selectedRoute value is "ROUTE_ADVISOR_QUEUE" — the conformant value from
the closed set enforced by atlas:RoutingPolicyShape. The prior value
"route_to_advisor" was not in the closed set and would fail SHACL.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict

from neptune_client import sparql_update

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Write the routing decision to the SLGD."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    household_uri = event.get("household_uri", "")
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    originating_banker_id = event.get("originating_banker_id", "")
    approved_rationale = event.get("approved_rationale", "")
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    routing_decision_uri = f"atlas:routing/{invocation_id}"

    # selectedRoute = "ROUTE_ADVISOR_QUEUE" — the conformant closed-set value.
    # atlas:RoutingPolicyShape (atlas-shapes.ttl) requires exactly one of:
    # ROUTE_ADVISOR_QUEUE, ROUTE_SUPPRESSION_LIST, ROUTE_ESCALATION.
    insert_sparql = f"""
    PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        <{routing_decision_uri}> a atlas:RoutingDecision ;
            atlas:selectedRoute "ROUTE_ADVISOR_QUEUE" ;
            atlas:targetAdvisor <{selected_advisor_uri}> ;
            atlas:aboutHousehold <{household_uri}> ;
            atlas:approvedRationale "{_escape_sparql(approved_rationale)}" ;
            prov:wasGeneratedBy <urn:atlas:referral-orchestrator> ;
            prov:wasAttributedTo <{originating_banker_id}> ;
            prov:generatedAtTime "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"^^xsd:dateTime .
    }}
    """

    try:
        sparql_update(insert_sparql)
    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return {**event, "status": "workflow_error", "error": str(exc)}

    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "event": "routing_decision_written",
        "routing_decision_uri": routing_decision_uri,
    }))
    return {**event, "status": "decision_written", "routing_decision_uri": routing_decision_uri}


def _escape_sparql(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
