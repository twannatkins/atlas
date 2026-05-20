"""
AppSync resolver Lambda — handles all SPARQL-backed GraphQL queries.

Translates GraphQL field selections into SPARQL queries, invokes
atlas-sparql-mcp, and shapes the response back into GraphQL types.

Handles: customer, household, searchCustomers, wealthSignals,
advisoryRelationships, referrals, auditTrail, themes.

The persona claim is extracted from the AppSync identity context
(Cognito JWT) and passed through to the MCP server for Lake Formation
scoping. The resolver does NOT make its own authorization decisions.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import prefixed, safe_uri, safe_int

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AppSync resolver entry point.

    AppSync sends a structured event with:
      - info.fieldName: the GraphQL field being resolved
      - arguments: the query arguments
      - identity: the Cognito identity (contains persona claim)
    """
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    field_name = event.get("info", {}).get("fieldName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})

    # Extract persona claim from Cognito JWT claims
    persona_claim = _extract_persona(identity)

    try:
        if field_name == "customer":
            return _resolve_customer(arguments, persona_claim)
        elif field_name == "household":
            return _resolve_household(arguments, persona_claim)
        elif field_name == "searchCustomers":
            return _resolve_search_customers(arguments, persona_claim)
        elif field_name == "wealthSignals":
            return _resolve_wealth_signals(arguments, persona_claim)
        elif field_name == "advisoryRelationships":
            return _resolve_advisory_relationships(arguments, persona_claim)
        elif field_name == "referrals":
            return _resolve_referrals(arguments, persona_claim)
        elif field_name == "auditTrail":
            return _resolve_audit_trail(arguments, persona_claim)
        elif field_name == "themes":
            return _resolve_themes(arguments, persona_claim)
        else:
            raise ValueError(f"Unknown field: {field_name}")

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "field": field_name,
            "error": str(exc),
        }))
        raise


def _extract_persona(identity: Dict[str, Any]) -> str:
    """Extract persona claim from AppSync Cognito identity context."""
    # AppSync passes Cognito claims in identity.claims
    claims = identity.get("claims", {})
    persona = claims.get("custom:persona", "")
    if not persona:
        # Fallback: check groups
        groups = claims.get("cognito:groups", [])
        if groups:
            persona = groups[0]
    return persona or "atlas-consumer-banker"


def _resolve_customer(args: Dict, persona: str) -> Dict[str, Any]:
    """Resolve a single customer by URI."""
    uri = safe_uri(args.get("uri", ""))
    sparql = prefixed(f"""
        SELECT ?customerId ?label WHERE {{
            <{uri}> a atlas:Customer ;
                atlas:customerId ?customerId .
            OPTIONAL {{ <{uri}> rdfs:label ?label }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    if not rows:
        return None
    row = rows[0]
    return {
        "uri": uri,
        "customerId": row.get("customerId", ""),
        "label": row.get("label", ""),
    }


def _resolve_household(args: Dict, persona: str) -> Dict[str, Any]:
    """Resolve a household by URI with members."""
    uri = safe_uri(args.get("uri", ""))
    sparql = prefixed(f"""
        SELECT ?label ?memberUri ?memberLabel WHERE {{
            <{uri}> a atlas:Household .
            OPTIONAL {{ <{uri}> rdfs:label ?label }}
            OPTIONAL {{
                ?memberUri atlas:memberOf <{uri}> .
                OPTIONAL {{ ?memberUri rdfs:label ?memberLabel }}
            }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    if not rows:
        return None

    members = [
        {"uri": r["memberUri"], "label": r.get("memberLabel", "")}
        for r in rows if r.get("memberUri")
    ]
    return {
        "uri": uri,
        "label": rows[0].get("label", ""),
        "members": members,
        "memberCount": len(members),
    }


def _resolve_search_customers(args: Dict, persona: str) -> List[Dict]:
    """Search customers — returns persona-scoped results."""
    limit = safe_int(args.get("limit", 20), max_val=100)
    sparql = prefixed(f"""
        SELECT ?uri ?customerId ?label WHERE {{
            ?uri a atlas:Customer ;
                atlas:customerId ?customerId .
            OPTIONAL {{ ?uri rdfs:label ?label }}
        }}
        LIMIT {limit}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {"uri": r["uri"], "customerId": r.get("customerId", ""), "label": r.get("label", "")}
        for r in rows
    ]


def _resolve_wealth_signals(args: Dict, persona: str) -> List[Dict]:
    """Resolve wealth signals for a customer."""
    customer_uri = safe_uri(args.get("customerUri", ""))
    sparql = prefixed(f"""
        SELECT ?uri ?signalType ?strength ?signalDate WHERE {{
            ?uri a atlas:WealthSignal ;
                atlas:aboutCustomer <{customer_uri}> ;
                atlas:hasSignalType ?signalType .
            OPTIONAL {{ ?uri atlas:signalStrength ?strength }}
            OPTIONAL {{ ?uri atlas:signalDate ?signalDate }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            "signalType": r.get("signalType", ""),
            "strength": r.get("strength", ""),
            "signalDate": r.get("signalDate"),
        }
        for r in rows
    ]


def _resolve_advisory_relationships(args: Dict, persona: str) -> List[Dict]:
    """Resolve advisory relationships for a customer."""
    customer_uri = safe_uri(args.get("customerUri", ""))
    sparql = prefixed(f"""
        SELECT ?uri ?advisorUri ?advisorLabel ?startDate ?endDate ?relType WHERE {{
            <{customer_uri}> atlas:hasAdvisor ?uri .
            ?uri atlas:coveringAdvisor ?advisorUri ;
                atlas:coverageStartDate ?startDate .
            OPTIONAL {{ ?advisorUri rdfs:label ?advisorLabel }}
            OPTIONAL {{ ?uri atlas:coverageEndDate ?endDate }}
            OPTIONAL {{ ?uri atlas:relationshipType ?relType }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            "advisor": {"uri": r.get("advisorUri", ""), "label": r.get("advisorLabel", "")},
            "coverageStartDate": r.get("startDate", ""),
            "coverageEndDate": r.get("endDate"),
            "relationshipType": r.get("relType", "Primary"),
            "isActive": r.get("endDate") is None,
        }
        for r in rows
    ]


def _resolve_referrals(args: Dict, persona: str) -> List[Dict]:
    """Resolve referrals for a household."""
    household_uri = safe_uri(args.get("householdUri", ""))
    sparql = prefixed(f"""
        SELECT ?uri ?rationale ?referralDate ?originatedBy ?routeUri ?selectedRoute WHERE {{
            ?uri a <https://github.com/your-org/atlas/ontology/part2#Referral> ;
                <https://github.com/your-org/atlas/ontology/part2#hasRoutingDecision> ?routeUri .
            ?routeUri atlas:aboutHousehold <{household_uri}> ;
                atlas:selectedRoute ?selectedRoute .
            OPTIONAL {{ ?uri <https://github.com/your-org/atlas/ontology/part2#hasApprovedRationale> ?rationale }}
            OPTIONAL {{ ?uri <https://github.com/your-org/atlas/ontology/part2#referralDate> ?referralDate }}
            OPTIONAL {{ ?uri <https://github.com/your-org/atlas/ontology/part2#originatedBy> ?originatedBy }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            "approvedRationale": r.get("rationale", ""),
            "referralDate": r.get("referralDate", ""),
            "originatedBy": r.get("originatedBy", ""),
            "routingDecision": {
                "uri": r.get("routeUri", ""),
                "selectedRoute": r.get("selectedRoute", ""),
            },
        }
        for r in rows
    ]


def _resolve_audit_trail(args: Dict, persona: str) -> List[Dict]:
    """Resolve audit records for a routing decision."""
    routing_uri = safe_uri(args.get("routingDecisionUri", ""))
    sparql = prefixed(f"""
        SELECT ?uri ?generatedAtTime ?workflowStatus WHERE {{
            ?uri a atlas:AuditRecord ;
                atlas:routingDecision <{routing_uri}> .
            OPTIONAL {{ ?uri prov:generatedAtTime ?generatedAtTime }}
            OPTIONAL {{ ?uri atlas:workflowStatus ?workflowStatus }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            "generatedAtTime": r.get("generatedAtTime", ""),
            "workflowStatus": r.get("workflowStatus", ""),
        }
        for r in rows
    ]


def _resolve_themes(args: Dict, persona: str) -> List[Dict]:
    """Resolve market themes (Phase 2)."""
    limit = safe_int(args.get("limit", 10), max_val=50)
    sparql = f"""
        PREFIX atlas-part-2: <https://github.com/your-org/atlas/ontology/part2#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?uri ?themeLabel ?themeDate WHERE {{
            ?uri a atlas-part-2:ThemeAssertion ;
                atlas-part-2:themeLabel ?themeLabel .
            OPTIONAL {{ ?uri atlas-part-2:themeDate ?themeDate }}
        }}
        LIMIT {limit}
    """
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            "themeLabel": r.get("themeLabel", ""),
            "themeDate": r.get("themeDate"),
            "sourceArticles": [],
        }
        for r in rows
    ]


def _query_sparql(sparql: str, persona_claim: str) -> List[Dict]:
    """Invoke atlas-sparql-mcp for a read query."""
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=SPARQL_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "query",
            "sparql": sparql,
            "persona_claim": persona_claim,
            "graph_tier": "slgd",
        }),
    )
    result = json.loads(response["Payload"].read())
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "SPARQL MCP error"))
    return result.get("rows", [])
