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
    info = event.get("info", {})
    field_name = info.get("fieldName", "")
    parent_type = info.get("parentTypeName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})
    # AppSync forwards the parent object on a nested-field resolver (default direct-Lambda
    # mapping sends the full $context). For Customer.wealthSignals the parent Customer is
    # in event["source"]; we scope the signal query to its uri.
    source = event.get("source") or {}
    # Extract the Cognito access token forwarded by AppSync — required for AgentCore auth.
    _current_bearer_token = (event.get("request") or {}).get("headers", {}).get("authorization", "")

    # Extract persona claim from Cognito JWT claims
    persona_claim = _extract_persona(identity)

    try:
        # Nested field resolvers (dispatch on the PARENT type, not just the field name —
        # `wealthSignals` exists on both Query (flat, arg customerUri) and Customer
        # (nested, parent uri)). The nested path reuses the SAME _resolve_wealth_signals
        # producesSignal logic, scoped to the parent customer's uri — one source of truth,
        # no duplicated SPARQL. Returns [] (not null) for customers with no signals, which
        # satisfies the non-nullable [WealthSignal!]! and lets the dashboard list render.
        if parent_type == "Customer" and field_name == "wealthSignals":
            # PERFORMANCE short-circuit: the dashboard's searchCustomers already fetched each
            # customer's signals in ONE batched SPARQL and attached them to the parent object.
            # When AppSync resolves the nested field it forwards that parent as `source`, so we
            # return the pre-fetched array WITHOUT another AgentCore round-trip (the N+1 killer).
            # Only the single-customer pages, whose parent has no pre-fetched signals, fall
            # through to the per-customer query.
            if "wealthSignals" in source:
                return source["wealthSignals"]
            return _resolve_wealth_signals({"customerUri": source.get("uri", "")}, persona_claim)
        # Customer.advisoryRelationships (nested) — the blocker: CLIENT_360_QUERY selects
        # this non-nullable [AdvisoryRelationship!]! field, but it had no resolver, so it
        # returned null and nulled the whole customer ("Client not found"). Same Pass-2c
        # fix as wealthSignals: reuse the flat _resolve_advisory_relationships scoped to the
        # parent customer's uri. Returns [] (not null) for a customer with no coverage,
        # which satisfies the non-nullable list.
        if parent_type == "Customer" and field_name == "advisoryRelationships":
            # Same N+1 short-circuit as wealthSignals: the wealth dashboard's
            # searchCustomers batched coverage onto the parent, so return it without
            # another round-trip. Single-customer pages fall through to the live query.
            if "advisoryRelationships" in source:
                return source["advisoryRelationships"]
            return _resolve_advisory_relationships({"customerUri": source.get("uri", "")}, persona_claim)
        # Customer.household (nested) — nullable, so it did not null the customer, but it
        # had no resolver so it always returned null. Resolve the customer's household via
        # the atlas:memberOf link, then reuse the flat household logic. null when the
        # customer is not in a household (the schema allows it).
        if parent_type == "Customer" and field_name == "household":
            return _resolve_customer_household(source.get("uri", ""), persona_claim)

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
        "label": _display_label(row.get("label", ""), row.get("customerId", ""), uri),
    }


def _resolve_household(args: Dict, persona: str) -> Dict[str, Any]:
    """Resolve a household by URI with members."""
    uri = safe_uri(args.get("uri", ""))
    sparql = prefixed(f"""
        SELECT ?label ?memberUri ?memberLabel ?memberCustomerId WHERE {{
            <{uri}> a atlas:Household .
            OPTIONAL {{ <{uri}> rdfs:label ?label }}
            OPTIONAL {{
                ?memberUri atlas:memberOf <{uri}> .
                OPTIONAL {{ ?memberUri rdfs:label ?memberLabel }}
                OPTIONAL {{ ?memberUri atlas:customerId ?memberCustomerId }}
            }}
        }}
    """)
    rows = _query_sparql(sparql, persona)
    if not rows:
        return None

    members = [
        {
            "uri": r["memberUri"],
            "label": _display_label(
                r.get("memberLabel", ""), r.get("memberCustomerId", ""), r["memberUri"]
            ),
        }
        for r in rows if r.get("memberUri")
    ]
    # The household itself has no rdfs:label either; give it a readable handle from its URI
    # tail (household-<short>) rather than a blank — same honest-presentation rule.
    hh_label = rows[0].get("label", "")
    if not hh_label:
        tail = uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        seg = tail.replace("household-", "").split("-")[0]
        hh_label = f"Household {seg}" if seg else tail
    return {
        "uri": uri,
        "label": hh_label,
        "members": members,
        "memberCount": len(members),
    }


def _resolve_customer_household(customer_uri: str, persona: str) -> Dict[str, Any]:
    """Resolve the household a customer belongs to (the nested Customer.household field).

    The flat _resolve_household takes a HOUSEHOLD uri; here the parent is a CUSTOMER, so we
    first follow the customer's atlas:memberOf link to its household, then reuse the flat
    logic for the household's members. Returns null when the customer is not in a household
    (Customer.household is nullable in the schema)."""
    uri = safe_uri(customer_uri)
    rows = _query_sparql(prefixed(f"""
        SELECT ?hh WHERE {{ <{uri}> atlas:memberOf ?hh . ?hh a atlas:Household . }} LIMIT 1
    """), persona)
    if not rows or not rows[0].get("hh"):
        return None
    return _resolve_household({"uri": rows[0]["hh"]}, persona)


def _display_label(raw_label: str, customer_id: str, uri: str = "") -> str:
    """A readable display label for a customer.

    The SLGD carries no rdfs:label on promoted customers — the ER promotion wrote
    atlas:customerId but no human name (05_entity_resolution.ipynb cell-08), and we will
    NOT fabricate one ("Rachel Kim"/"Marcus Webb" in the design mockups are illustrative,
    not data). When a real rdfs:label exists we use it; otherwise we derive a short,
    honest handle from the REAL customerId — e.g. "Customer c6b6e4ad" — so the UI shows a
    stable identifier a human can read and match to the URI, not a 36-char UUID and not an
    invented name. Presentation only; the authoritative id (customerId/uri) is unchanged.
    """
    if raw_label:
        return raw_label
    cid = (customer_id or "").strip()
    if cid:
        # UUID-style id → first segment is a stable, short, recognizable handle.
        short = cid.split("-")[0] if "-" in cid else cid
        return f"Customer {short}"
    return ""


def _resolve_search_customers(args: Dict, persona: str) -> List[Dict]:
    """Search customers — returns persona-scoped results.

    Ordering: customers that have at least one derived wealth signal sort FIRST (the
    actionable book), then the rest. Without this the dashboard leads with a wall of
    signal-less customers (most of the 200) and the signalled ones — the whole point of
    the screen — are buried past the limit. The ORDER BY keys off a real fact
    (EXISTS producesSignal), not a fabricated score.
    """
    limit = safe_int(args.get("limit", 20), max_val=100)
    # PERFORMANCE — this query fetches each customer's wealth signals IN THE SAME SPARQL
    # via GROUP_CONCAT, so the dashboard is ONE resolver→MCP→Neptune round-trip instead of
    # 1 + N (the old shape: list 50 customers, then a separate nested wealthSignals call per
    # customer = 51 AgentCore invocations, each carrying a ~3.5s invoke_agent_runtime floor
    # → ~24s). Each AgentCore invocation is the dominant cost (the Neptune SELECT itself is
    # ~200ms), so collapsing 51→1 is the fix. The nested Customer.wealthSignals resolver
    # short-circuits when the parent object already carries `wealthSignals` (see handler),
    # so no per-customer calls fire for the dashboard.
    #
    # Signals are packed as "sigUri|||type|||date|||evidence" rows joined by a multi-char
    # ASCII record token that cannot occur in a URI/label, then GROUP_CONCAT per customer.
    # One row per customer (GROUP BY), still signalled-first. Plain ASCII tokens avoid any
    # SPARQL control-char escaping ambiguity across engines.
    sep = "@@SIG@@"  # record separator between signals
    fsep = "|||"     # field separator within a signal
    # CRITICAL: the customer LIMIT is applied in an INNER subquery FIRST, then signals are
    # joined only for that page. A flat GROUP_CONCAT with the LIMIT on the outside makes
    # Neptune materialize signals for ALL 200 customers before truncating — which times out
    # (>35s). With the inner LIMIT the outer join touches only `limit` customers; measured
    # ~5s for limit=50 (essentially the AgentCore invoke floor — the query work is ~0).
    # The inner EXISTS computes signalled-first ordering without joining signal rows.
    # Both the wealth-readiness signals AND the advisory coverage are batched here via
    # GROUP_CONCAT, so BOTH the wholesale dashboard (signals) and the wealth dashboard
    # (coverage) are a single round-trip — the nested Customer.wealthSignals and
    # Customer.advisoryRelationships resolvers short-circuit on the pre-fetched arrays.
    sparql = prefixed(f"""
        SELECT ?uri ?customerId ?label
               (GROUP_CONCAT(DISTINCT ?sigpack ; SEPARATOR="{sep}") AS ?sigs)
               (GROUP_CONCAT(DISTINCT ?covpack ; SEPARATOR="{sep}") AS ?covs) WHERE {{
            {{
                SELECT ?uri ?customerId ?label
                       (EXISTS {{ ?uri atlas:producesSignal ?x }} AS ?hasSignal) WHERE {{
                    ?uri a atlas:Customer ;
                        atlas:customerId ?customerId .
                    OPTIONAL {{ ?uri rdfs:label ?label }}
                }}
                ORDER BY DESC(?hasSignal) ?customerId
                LIMIT {limit}
            }}
            OPTIONAL {{
                ?uri atlas:producesSignal ?uri_sig .
                ?uri_sig atlas:hasSignalType ?sigType .
                OPTIONAL {{ ?sigType skos:prefLabel ?sigLabel }}
                OPTIONAL {{ ?uri_sig atlas:signalDate ?sigDate }}
                OPTIONAL {{ ?uri_sig atlas:evidencedBy ?sigEvidence }}
                BIND(CONCAT(STR(?uri_sig), "{fsep}",
                            STR(COALESCE(?sigLabel, ?sigType)), "{fsep}",
                            STR(COALESCE(?sigDate, "")), "{fsep}",
                            STR(COALESCE(?sigEvidence, ""))) AS ?sigpack)
            }}
            OPTIONAL {{
                ?uri atlas:hasAdvisor ?rel .
                ?rel atlas:coveringAdvisor ?advUri .
                OPTIONAL {{ ?advUri rdfs:label ?advLabel }}
                OPTIONAL {{ ?rel atlas:coverageStartDate ?covStart }}
                OPTIONAL {{ ?rel atlas:coverageEndDate ?covEnd }}
                BIND(CONCAT(STR(?rel), "{fsep}",
                            STR(COALESCE(?advLabel, ?advUri)), "{fsep}",
                            STR(COALESCE(?covStart, "")), "{fsep}",
                            STR(COALESCE(?covEnd, ""))) AS ?covpack)
            }}
        }}
        GROUP BY ?uri ?customerId ?label
    """)
    rows = _query_sparql(sparql, persona)
    out: List[Dict] = []
    for r in rows:
        out.append({
            "uri": r["uri"],
            "customerId": r.get("customerId", ""),
            "label": _display_label(r.get("label", ""), r.get("customerId", ""), r["uri"]),
            # Attach signals + coverage parsed from the packed GROUP_CONCATs. AppSync's
            # nested Customer.wealthSignals / Customer.advisoryRelationships resolvers find
            # these already on `source` and return them WITHOUT a per-customer round-trip
            # (see handler short-circuits).
            "wealthSignals": _unpack_signals(r.get("sigs", "")),
            "advisoryRelationships": _unpack_coverage(r.get("covs", "")),
        })
    return out


def _unpack_signals(packed: str) -> List[Dict]:
    """Parse the GROUP_CONCAT signal blob from _resolve_search_customers into signal objects.

    Format: "<sigUri>|||<type>|||<date>|||<evidence>" rows joined by U+241E. Empty blob
    (a customer with no signals) → []. Provenance is built the same truthful way as the
    standalone wealthSignals resolver (validatedBy = the universal shape; derivedFrom = the
    real evidencedBy txn when present).
    """
    if not packed:
        return []
    out: List[Dict] = []
    for rec in packed.split("@@SIG@@"):
        if not rec:
            continue
        parts = rec.split("|||")
        if len(parts) < 2 or not parts[0]:
            continue
        sig_uri, sig_type = parts[0], parts[1]
        sig_date = parts[2] if len(parts) > 2 else ""
        evidence = parts[3] if len(parts) > 3 else ""
        out.append({
            "uri": sig_uri,
            "signalType": sig_type,
            "strength": "",
            "signalDate": _as_datetime(sig_date) if sig_date else None,
            "provenance": _signal_provenance(sig_type, evidence),
        })
    return out


def _unpack_coverage(packed: str) -> List[Dict]:
    """Parse the GROUP_CONCAT advisory-coverage blob into AdvisoryRelationship objects.

    Format: "<relUri>|||<advisorLabel>|||<startDate>|||<endDate>" rows joined by the
    record token. Empty blob → []. isActive = no coverageEndDate (the same rule as the
    standalone advisoryRelationships resolver). Powers the wealth dashboard's coverage
    tags and CoverageStrip in ONE round-trip (the nested resolver short-circuits).
    """
    if not packed:
        return []
    out: List[Dict] = []
    for rec in packed.split("@@SIG@@"):
        if not rec:
            continue
        parts = rec.split("|||")
        if len(parts) < 2 or not parts[0]:
            continue
        rel_uri, advisor_label = parts[0], parts[1]
        start = parts[2] if len(parts) > 2 else ""
        end = parts[3] if len(parts) > 3 else ""
        out.append({
            "uri": rel_uri,
            "advisor": {"uri": "", "label": advisor_label},
            "coverageStartDate": start or "",
            "coverageEndDate": end or None,
            "relationshipType": "Primary",
            "isActive": not end,
        })
    return out


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
        SELECT DISTINCT ?uri ?signalType ?signalLabel ?strength ?signalDate ?evidence WHERE {{
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
            # The transaction/observation that evidenced this signal — written by the
            # derivation CONSTRUCT (05_entity_resolution.ipynb cell-21) as atlas:evidencedBy.
            # OPTIONAL: the HouseholdAggregation rule does not stamp a single evidence txn.
            OPTIONAL {{ ?uri_sig atlas:evidencedBy ?evidence }}
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
            # Provenance derived ONLY from facts that genuinely hold for this node — no
            # fabrication. validatedBy is the SHACL shape that gates EVERY WealthSignal at
            # write time (atlas:WealthSignalTypeShape, atlas-shapes.ttl:81; the derivation
            # validates against it before INSERT, cell-24) — so it is true for every signal
            # returned here. derivedFrom is the signal's real atlas:evidencedBy source when
            # present (the actual transaction that evidenced it), else omitted. The signal
            # type itself is the generating process.
            "provenance": _signal_provenance(
                r.get("signalType", ""), r.get("evidence", "")
            ),
        }
        for r in rows
    ]


def _signal_provenance(signal_type_uri: str, evidence_uri: str) -> Dict[str, Any]:
    """Build a truthful Provenance object for a wealth signal.

    Every field is a fact that holds for the node — nothing is invented:
      - validatedBy: atlas:WealthSignalTypeShape gates every atlas:WealthSignal before it
        is written (atlas-shapes.ttl Shape 5; the live derivation runs pyshacl against it
        and INSERTs only on conform — 05_entity_resolution.ipynb cell-24). Universal, real.
      - derivedFrom: the signal's own atlas:evidencedBy source (the transaction the
        derivation pattern-matched). Omitted when absent (e.g. the household-aggregation
        rule attaches no single evidence txn) rather than guessed.
      - generatedBy: the signal type is the named derivation rule that produced it.
    """
    prov: Dict[str, Any] = {"validatedBy": "atlas:WealthSignalTypeShape"}
    if evidence_uri:
        prov["derivedFrom"] = evidence_uri
    if signal_type_uri:
        prov["generatedBy"] = signal_type_uri
    return prov


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
