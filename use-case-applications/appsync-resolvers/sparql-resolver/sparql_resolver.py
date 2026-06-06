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

# atlas_sparql.py is vendored alongside this file for Lambda deployment.
# The WS1 shared module is at agentic-semantic-layer/notebooks/shared/atlas_sparql.py —
# copied here via CDK asset bundling so Lambda can import it.
sys.path.insert(0, os.path.dirname(__file__))

from atlas_sparql import prefixed, safe_uri, safe_int

import urllib.parse
import urllib.request

import boto3  # used by the staged SigV4 transport (_invoke_agentcore_sigv4)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")

# ── AgentCore invoke transport ───────────────────────────────────────────────
# Two transports exist; MCP_AUTH_MODE selects which is live:
#
#   "bearer" (DEFAULT — the live path): the runtimes use a Cognito customJWTAuthorizer,
#     so the caller forwards the user's access token as Bearer in a plain HTTPS POST.
#     boto3's invoke_agent_runtime uses SigV4 and cannot inject a custom Authorization
#     header, so we POST with urllib. This is the path the live card reads through.
#
#   "sigv4" (Option-A Pass 2 — NOT live until the coordinated cutover): the runtimes'
#     authorizer is flipped Cognito->IAM, and this resolver invokes via the boto3 SDK
#     (SigV4-signed by the Lambda execution role). This MUST be flipped in lockstep with
#     the authorizer (a runtime has ONE authorizer) — setting MCP_AUTH_MODE=sigv4 while
#     the authorizer is still Cognito would break the read path. Pass 2 sets the env var,
#     flips the authorizer, and grants bedrock-agentcore:InvokeAgentRuntime together.
#
# The SigV4 helper mirrors the agents' canonical, in-repo call
# (agents/nl-to-sparql-agent/nl_to_sparql_agent.py:206-222): same ARN, same payload
# dict, same response unwrap (response["response"].read()).
MCP_AUTH_MODE = os.environ.get("MCP_AUTH_MODE", "bearer")


def _agentcore_endpoint(runtime_arn: str) -> str:
    encoded = urllib.parse.quote(runtime_arn, safe="")
    return f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{encoded}/invocations"


def _invoke_agentcore_bearer(runtime_arn: str, payload: Dict, bearer_token: str) -> Dict:
    """LIVE path: POST to an AgentCore runtime with the user's JWT as Bearer."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(_agentcore_endpoint(runtime_arn), data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {bearer_token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _invoke_agentcore_sigv4(runtime_arn: str, payload: Dict) -> Dict:
    """Pass-2 path (staged, not live until MCP_AUTH_MODE=sigv4 + authorizer=IAM).

    Mirrors the agents' proven-correct SDK call. The Lambda execution role's IAM
    identity signs the request (SigV4); no user token is forwarded.
    """
    client = boto3.client("bedrock-agentcore")
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps(payload).encode(),
        contentType="application/json",
    )
    return json.loads(response["response"].read())


def _invoke_agentcore(runtime_arn: str, payload: Dict, bearer_token: str) -> Dict:
    """Transport dispatch. Default 'bearer' keeps the live read path unchanged; Pass 2
    sets MCP_AUTH_MODE=sigv4 in lockstep with the authorizer flip. The bearer_token arg
    is retained for call-site compatibility and ignored in sigv4 mode."""
    if MCP_AUTH_MODE == "sigv4":
        return _invoke_agentcore_sigv4(runtime_arn, payload)
    return _invoke_agentcore_bearer(runtime_arn, payload, bearer_token)

# Bearer token extracted from the AppSync request headers — threaded through all resolvers.
_current_bearer_token: str = ""


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AppSync resolver entry point.

    AppSync sends a structured event with:
      - info.fieldName: the GraphQL field being resolved
      - arguments: the query arguments
      - identity: the Cognito identity (contains persona claim)
    """
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    global _current_bearer_token
    field_name = event.get("info", {}).get("fieldName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})
    # Extract the Cognito access token forwarded by AppSync — required for AgentCore auth.
    _current_bearer_token = (event.get("request") or {}).get("headers", {}).get("authorization", "")

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
    """Resolve wealth signals for a customer OR a household.

    The authoritative link is atlas:producesSignal (Customer -> WealthSignal),
    per the ontology (atlas-core.ttl:378-383) and the derivation CONSTRUCT
    (05_entity_resolution.ipynb). The prior query used atlas:aboutCustomer, a
    predicate that exists in neither the ontology nor the data, so it returned []
    for every URI.

    The argument may be a customer URI (direct producer) or a household URI (the
    referral screen is household-scoped). The UNION handles both: a direct match,
    plus a one-hop atlas:memberOf traversal so a household aggregates its members'
    signals. SELECT DISTINCT de-duplicates shared HouseholdAggregation signals
    (signal-has-*) that multiple members produce.

    signalStrength is OPTIONAL and absent in the current synthetic data — it
    renders empty rather than fabricated.
    """
    uri = safe_uri(args.get("customerUri", ""))
    sparql = prefixed(f"""
        SELECT DISTINCT ?uri ?signalType ?signalLabel ?strength ?signalDate WHERE {{
            {{ <{uri}> atlas:producesSignal ?uri_sig }}
            UNION
            {{ ?member atlas:memberOf <{uri}> ;
                       atlas:producesSignal ?uri_sig }}
            ?uri_sig a atlas:WealthSignal ;
                atlas:hasSignalType ?signalType .
            BIND(?uri_sig AS ?uri)
            # Join the SKOS prefLabel for the signal type when it is loaded in the
            # SLGD (WS1 types are; WS2 atlas-part-2: types are not yet — see Pass 2).
            # OPTIONAL so an unlabeled type still returns; we fall back to the URI below.
            OPTIONAL {{ ?signalType skos:prefLabel ?signalLabel }}
            OPTIONAL {{ ?uri_sig atlas:signalStrength ?strength }}
            OPTIONAL {{ ?uri_sig atlas:signalDate ?signalDate }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    return [
        {
            "uri": r["uri"],
            # Prefer the human-readable SKOS prefLabel; fall back to the type URI
            # when the concept (and its label) is not loaded in the SLGD.
            "signalType": r.get("signalLabel") or r.get("signalType", ""),
            "strength": r.get("strength", ""),
            # signalDate is typed AWSDateTime in the schema, but the derivation
            # writes a bare xsd:date (e.g. "2026-03-03"). Normalize a date-only
            # value to a valid AWSDateTime so AppSync can serialize it; pass through
            # anything that already carries a time component, and leave null as null.
            "signalDate": _as_datetime(r.get("signalDate")),
        }
        for r in rows
    ]


def _as_datetime(value):
    """Coerce a bare YYYY-MM-DD date to an AWSDateTime (midnight UTC).

    The schema field is AWSDateTime; the SLGD stores signalDate as xsd:date with
    no time component, which the AWSDateTime scalar rejects. This is output
    normalization only — it does not change the stored triple.
    """
    if not value:
        return None
    if len(value) == 10 and value.count("-") == 2:
        return f"{value}T00:00:00Z"
    return value


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
    """Invoke atlas-sparql-mcp via AgentCore HTTP."""
    result = _invoke_agentcore(SPARQL_MCP_ARN, {
        "operation": "query",
        "sparql": sparql,
        "persona_claim": persona_claim,
        "graph_tier": "slgd",
    }, _current_bearer_token)
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "SPARQL MCP error"))
    return result.get("rows", [])
