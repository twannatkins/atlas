"""
audit-write — Step Functions sub-Lambda #5.

Writes the complete handoff record to atlas:AuditRecord with PROV-O
attribution. This is the final step in the orchestration workflow.
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

from atlas_sparql import prefixed

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Write the audit record to the SLGD."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    household_uri = event.get("household_uri", "")
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    originating_banker_id = event.get("originating_banker_id", "")
    routing_decision_uri = event.get("routing_decision_uri", "")
    signal_uris = event.get("signal_uris", [])
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    audit_record_uri = f"atlas:audit/{invocation_id}"

    # Build audit INSERT with full PROV-O attribution
    signals_triples = "\n".join(
        f'        <{audit_record_uri}> atlas:referencesSignal <{s}> .'
        for s in signal_uris
    )

    insert_sparql = f"""
    PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        <{audit_record_uri}> a atlas:AuditRecord ;
            atlas:aboutHousehold <{household_uri}> ;
            atlas:routingDecision <{routing_decision_uri}> ;
            atlas:targetAdvisor <{selected_advisor_uri}> ;
            prov:wasAttributedTo <{originating_banker_id}> ;
            prov:wasGeneratedBy <urn:atlas:referral-orchestrator> ;
            prov:generatedAtTime "{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"^^xsd:dateTime ;
            atlas:workflowStatus "completed" .
{signals_triples}
    }}
    """

    try:
        lambda_client = boto3.client("lambda")
        response = lambda_client.invoke(
            FunctionName=SPARQL_MCP_ARN,
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "operation": "update",
                "sparql": insert_sparql,
                "persona_claim": persona_claim,
            }),
        )
        result = json.loads(response["Payload"].read())
        if result.get("status") == "error":
            return {**event, "status": "workflow_error", "error": result.get("message", "Audit write failed")}
    except Exception as exc:
        return {**event, "status": "workflow_error", "error": str(exc)}

    return {
        **event,
        "status": "routed",
        "audit_record_uri": audit_record_uri,
    }
