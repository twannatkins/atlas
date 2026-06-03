"""
select-advisor — Step Functions sub-Lambda #1.

Queries the SLGD for advisors and selects a candidate for the referral.
Calls Neptune directly (SigV4 POST) — the AgentCore SPARQL MCP runtime
uses JWT-only auth with no backend SigV4 path.

Advisor predicate inventory (confirmed from SLGD):
  atlas:advisorId, rdf:type, atlas:promotedFrom, atlas:promotedBy.
rdfs:label and atlas:currentCapacity are NOT populated for synthetic
advisors. Selection is first-match (capacity ranking deferred to when
real advisor data is available).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict

from neptune_client import sparql_query

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ADVISOR_QUERY uses only populated predicates (advisorId confirmed in SLGD).
# rdfs:label and atlas:currentCapacity are absent in synthetic data — querying
# them would return zero rows. Label falls back to the advisorId.
ADVISOR_QUERY = """
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
SELECT ?advisor ?advisorId WHERE {
    ?advisor a atlas:Advisor ;
             atlas:advisorId ?advisorId .
}
LIMIT 9
"""


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Select an eligible advisor for the referral."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))

    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    try:
        advisors = sparql_query(ADVISOR_QUERY, graph_tier="slgd")

        if not advisors:
            logger.warning(json.dumps({"invocation_id": invocation_id, "warning": "No advisors found in SLGD"}))
            return {**event, "status": "no_eligible_advisor", "selected_advisor_uri": "", "candidates": []}

        selected = advisors[0]
        advisor_uri = selected.get("advisor", "")
        advisor_label = selected.get("advisorId", advisor_uri)  # fallback to ID

        logger.info(json.dumps({
            "invocation_id": invocation_id,
            "event": "advisor_selected",
            "advisor_uri": advisor_uri,
            "total_candidates": len(advisors),
        }))

        return {
            **event,
            "status": "advisor_selected",
            "selected_advisor_uri": advisor_uri,
            "selected_advisor_label": advisor_label,
            "candidates": advisors[:5],
        }

    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return {**event, "status": "no_eligible_advisor", "error": str(exc)}
