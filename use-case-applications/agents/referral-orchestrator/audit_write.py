"""
audit-write — Step Functions sub-Lambda #5.

Writes atlas:AuditRecord with PROV-O attribution.
Calls Neptune directly (SigV4 POST UPDATE).
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
    """Write the audit record to the SLGD."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    household_uri = event.get("household_uri", "")
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    originating_banker_id = event.get("originating_banker_id", "")
    routing_decision_uri = event.get("routing_decision_uri", "")
    signal_uris = event.get("signal_uris", [])

    audit_record_uri = f"atlas:audit/{invocation_id}"

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
        sparql_update(insert_sparql)
    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return {**event, "status": "workflow_error", "error": str(exc)}

    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "event": "audit_written",
        "audit_record_uri": audit_record_uri,
    }))
    return {
        **event,
        "status": "routed",
        "audit_record_uri": audit_record_uri,
    }
