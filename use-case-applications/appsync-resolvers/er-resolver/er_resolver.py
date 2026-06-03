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

import urllib.parse
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ER_MCP_ARN = os.environ.get("ER_MCP_ARN", "")
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")

def _agentcore_endpoint(runtime_arn: str) -> str:
    encoded = urllib.parse.quote(runtime_arn, safe="")
    return f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{encoded}/invocations"

def _invoke_agentcore(runtime_arn: str, payload: Dict, bearer_token: str) -> Dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(_agentcore_endpoint(runtime_arn), data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {bearer_token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

_current_bearer_token: str = ""

sys.path.insert(0, os.path.dirname(__file__))

from atlas_sparql import prefixed, safe_uri


def handler(event: Dict[str, Any], context: Any) -> Any:
    """AppSync resolver entry point for Entity Resolution."""
    global _current_bearer_token
    field_name = event.get("info", {}).get("fieldName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})
    _current_bearer_token = (event.get("request") or {}).get("headers", {}).get("authorization", "")

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

    # Step 1: Look up canonical URI via atlas-er-mcp (AgentCore HTTP)
    er_result = _invoke_agentcore(ER_MCP_ARN, {
        "operation": "lookup",
        "source_system": source_system,
        "source_id": source_id,
    }, _current_bearer_token)

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

    # Step 2: Fetch customer data via atlas-sparql-mcp (AgentCore HTTP)
    sparql_result = _invoke_agentcore(SPARQL_MCP_ARN, {
        "operation": "query",
        "sparql": sparql,
        "persona_claim": persona,
        "graph_tier": "slgd",
    }, _current_bearer_token)
    rows = sparql_result.get("rows", [])

    if not rows:
        return {"uri": canonical_uri, "customerId": "", "label": ""}

    return {
        "uri": canonical_uri,
        "customerId": rows[0].get("customerId", ""),
        "label": rows[0].get("label", ""),
    }
