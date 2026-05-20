"""
AppSync resolver Lambda — handles Entity Resolution queries.

Translates the resolveEntity GraphQL query into an atlas-er-mcp lookup,
then fetches the resolved customer via the SPARQL resolver pattern.

Handles: resolveEntity.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ER_MCP_ARN = os.environ.get("ER_MCP_ARN", "")
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import prefixed, safe_uri


def handler(event: Dict[str, Any], context: Any) -> Any:
    """AppSync resolver entry point for Entity Resolution."""
    field_name = event.get("info", {}).get("fieldName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})

    persona_claim = _extract_persona(identity)

    if field_name == "resolveEntity":
        return _resolve_entity(arguments, persona_claim)
    else:
        raise ValueError(f"Unknown field: {field_name}")


def _extract_persona(identity: Dict[str, Any]) -> str:
    claims = identity.get("claims", {})
    persona = claims.get("custom:persona", "")
    if not persona:
        groups = claims.get("cognito:groups", [])
        if groups:
            persona = groups[0]
    return persona or "atlas-consumer-banker"


def _resolve_entity(args: Dict, persona: str) -> Dict[str, Any] | None:
    """Resolve a source-system ID to a canonical customer."""
    source_system = args.get("sourceSystem", "")
    source_id = args.get("sourceId", "")

    # Step 1: Look up canonical URI via atlas-er-mcp
    lambda_client = boto3.client("lambda")
    er_response = lambda_client.invoke(
        FunctionName=ER_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "lookup",
            "source_system": source_system,
            "source_id": source_id,
        }),
    )
    er_result = json.loads(er_response["Payload"].read())

    if er_result.get("status") != "success":
        return None

    canonical_uri = er_result.get("canonical_uri", "")
    if not canonical_uri:
        return None

    # Validate the canonical URI before interpolation — the ER MCP is a trusted
    # internal source but we still enforce IRI-safety as defense in depth.
    canonical_uri = safe_uri(canonical_uri, allow_any_scheme=True)

    # Step 2: Fetch customer data via SPARQL
    sparql = prefixed(f"""
        SELECT ?customerId ?label WHERE {{
            <{canonical_uri}> a atlas:Customer ;
                atlas:customerId ?customerId .
            OPTIONAL {{ <{canonical_uri}> rdfs:label ?label }}
        }}
    """)

    sparql_response = lambda_client.invoke(
        FunctionName=SPARQL_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "query",
            "sparql": sparql,
            "persona_claim": persona,
            "graph_tier": "slgd",
        }),
    )
    sparql_result = json.loads(sparql_response["Payload"].read())
    rows = sparql_result.get("rows", [])

    if not rows:
        return {"uri": canonical_uri, "customerId": "", "label": ""}

    return {
        "uri": canonical_uri,
        "customerId": rows[0].get("customerId", ""),
        "label": rows[0].get("label", ""),
    }
