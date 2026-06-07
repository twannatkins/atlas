"""
AppSync resolver Lambda — handles registry and agent invocation queries.

Translates GraphQL capabilities query and mutations into atlas-registry-mcp
calls. Passes persona claim from Cognito JWT through to the registry for
persona-scoped discovery.

Handles: capabilities, routeReferral, askGraph, draftRationale, suggestedQuestions,
converse.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any, Dict

import urllib.parse
import urllib.request

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGISTRY_MCP_ARN = os.environ.get("REGISTRY_MCP_ARN", "")
# referral-orchestrator Step Functions state machine — routeReferral starts an
# execution here directly (the proven path; see Pass 2). The prior route through
# registry-mcp invoke_capability → invoke_agent(agentName=…) used a boto3 method
# that does not exist on the bedrock-agentcore client and always raised.
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")

# Agent runtime ARNs for the action-side fields (askGraph / draftRationale). These are
# invoked DIRECTLY by ARN via _invoke_agentcore (SigV4 post-Option-A) — NOT through
# registry-mcp invoke_capability, which is the broken invoke_agent(agentName=…) path.
NL_TO_SPARQL_ARN = os.environ.get("NL_TO_SPARQL_ARN", "")
DRAFTER_ARN = os.environ.get("DRAFTER_ARN", "")
# conversational-context-manager — the #5 wealth conversation. Single-turn: it wraps
# nl-to-sparql-agent and its Memory calls no-op, so each turn is independent.
CONVERSATIONAL_ARN = os.environ.get("CONVERSATIONAL_ARN", "")
# ground-truth.yaml is the SAME template source nl-to-sparql-agent matches against;
# suggestedQuestions reads its question: lines so the UI's suggestions never drift from
# what the agent can actually answer. WS1-owned file — READ only, never written here.
GROUND_TRUTH_S3_URI = os.environ.get("GROUND_TRUTH_S3_URI", "")

# ── AgentCore invoke transport ───────────────────────────────────────────────
# MCP_AUTH_MODE selects transport (see sparql_resolver for the full rationale):
#   "sigv4" (DEFAULT, live post Option-A): boto3 invoke_agent_runtime, signed by the
#     Lambda role (the runtime authorizer is IAM).
#   "bearer" (rollback): forward the user's JWT as Bearer over a urllib POST (Cognito
#     authorizer). Moves in lockstep with the authorizer in agentcore-runtimes.ts.
# NOTE: routeReferral does NOT use this helper — it calls stepfunctions.start_execution.
# _invoke_agentcore is used by capabilities (-> registry-mcp) and the action-side fields
# askGraph/draftRationale/converse (-> their agents directly by ARN).
MCP_AUTH_MODE = os.environ.get("MCP_AUTH_MODE", "bearer")


def _agentcore_endpoint(runtime_arn: str) -> str:
    encoded = urllib.parse.quote(runtime_arn, safe="")
    return f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{encoded}/invocations"


def _invoke_agentcore_bearer(runtime_arn: str, payload: Dict, bearer_token: str) -> Dict:
    """LIVE path: POST with the user's JWT as Bearer."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(_agentcore_endpoint(runtime_arn), data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {bearer_token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _invoke_agentcore_sigv4(runtime_arn: str, payload: Dict) -> Dict:
    """Pass-2 path (staged): boto3 SDK, SigV4-signed by the Lambda role. Mirrors the
    agents' proven-correct call (nl_to_sparql_agent.py:206-222)."""
    client = boto3.client("bedrock-agentcore")
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps(payload).encode(),
        contentType="application/json",
    )
    return json.loads(response["response"].read())


def _invoke_agentcore(runtime_arn: str, payload: Dict, bearer_token: str) -> Dict:
    """Transport dispatch; default 'bearer' keeps the live path unchanged."""
    if MCP_AUTH_MODE == "sigv4":
        return _invoke_agentcore_sigv4(runtime_arn, payload)
    return _invoke_agentcore_bearer(runtime_arn, payload, bearer_token)

_current_bearer_token: str = ""


def handler(event: Dict[str, Any], context: Any) -> Any:
    """AppSync resolver entry point for registry operations."""
    global _current_bearer_token
    field_name = event.get("info", {}).get("fieldName", "")
    arguments = event.get("arguments", {})
    identity = event.get("identity", {})
    _current_bearer_token = (event.get("request") or {}).get("headers", {}).get("authorization", "")

    persona_claim = _extract_persona(identity)

    try:
        if field_name == "capabilities":
            return _resolve_capabilities(arguments, persona_claim)
        elif field_name == "routeReferral":
            return _resolve_route_referral(arguments, persona_claim, identity)
        elif field_name == "askGraph":
            return _resolve_ask_graph(arguments, persona_claim)
        elif field_name == "draftRationale":
            return _resolve_draft_rationale(arguments, persona_claim)
        elif field_name == "suggestedQuestions":
            return _resolve_suggested_questions()
        elif field_name == "converse":
            return _resolve_converse(arguments, persona_claim)
        else:
            raise ValueError(f"Unknown field: {field_name}")
    except Exception as exc:
        logger.error(json.dumps({"field": field_name, "error": str(exc)}))
        raise


def _extract_persona(identity: Dict[str, Any]) -> str:
    """Extract persona claim from AppSync Cognito identity context."""
    claims = identity.get("claims", {})
    persona = claims.get("custom:persona", "")
    if not persona:
        groups = claims.get("cognito:groups", [])
        if groups:
            persona = groups[0]
    return persona or "atlas-consumer-banker"


def _resolve_capabilities(args: Dict, persona: str) -> list:
    """Resolve the capability palette for the current persona."""
    persona_claim = args.get("personaClaim", persona)

    result = _invoke_registry("list_capabilities", {"persona_claim": persona_claim})
    agents = result.get("agents", [])
    mcp_servers = result.get("mcp_servers", [])

    # Map to GraphQL Capability type.
    # Supports both shapes:
    #   - AWS Agent Registry records (nested registryMetadata with snake_case keys)
    #   - ATLAS embedded fallback descriptors (flat camelCase keys on the agent dict)
    capabilities = []
    for agent in agents:
        meta = agent.get("registryMetadata", agent.get("registry_metadata", {}))
        capabilities.append({
            "name": agent.get("agentName", agent.get("name", "")),
            "displayName": meta.get("display_name", agent.get("displayName", "")),
            "displayIcon": meta.get("display_icon", agent.get("displayIcon", "")),
            "posture": agent.get("posture", ""),
            "capabilityTag": meta.get("capability_tag", agent.get("capabilityTag", "")),
            "phase": meta.get("phase", agent.get("phase", 1)),
        })
    return capabilities


def _resolve_route_referral(args: Dict, persona: str, identity: Dict) -> Dict:
    """Route a referral by starting the referral-orchestrator Step Functions
    execution directly — the proven path (Pass 2).

    The orchestrator state machine validates the input and runs the five-step
    chain (select_advisor → validate_routing[SHACL gate] → write_routing_decision
    → notify_advisor → audit_write). Its step Lambdas reach Neptune directly via
    SigV4; this resolver only needs states:StartExecution.

    The persona restriction (atlas-consumer-banker only) is enforced both here and
    inside the orchestrator (referral_orchestrator.py:63).
    """
    if persona != "atlas-consumer-banker":
        raise RuntimeError("Only atlas-consumer-banker can route referrals")
    if not STATE_MACHINE_ARN:
        raise RuntimeError("STATE_MACHINE_ARN is not configured on the resolver")

    # Originating banker: prefer the explicit arg, else the JWT subject.
    sub = identity.get("claims", {}).get("sub", "")
    originating_banker_id = args.get("originatingBankerId") or sub

    # Pass invocation_id into the execution so the step Lambdas mint the
    # RoutingDecision/AuditRecord URIs from it (write_routing_decision reads
    # event["invocation_id"]) — this makes the URI we return below match what
    # actually lands in the SLGD.
    invocation_id = str(uuid.uuid4())
    execution_input = {
        "household_uri": args["householdUri"],
        "signal_uris": args["signalUris"],
        "approved_rationale": args["approvedRationale"],
        "originating_banker_id": originating_banker_id,
        "persona_claim": persona,
        "invocation_id": invocation_id,
    }

    try:
        sfn = boto3.client("stepfunctions")
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"referral-{invocation_id}",
            input=json.dumps(execution_input),
        )
    except Exception as exc:
        logger.error(json.dumps({"event": "route_referral_failed", "error": str(exc)}))
        raise RuntimeError(f"Failed to start referral routing: {exc}")

    # The execution runs asynchronously; the RoutingDecision URI is minted inside
    # the workflow (write_routing_decision). We return the deterministic URI shape
    # the orchestrator uses (atlas:routing/<invocation_id>) and the conformant route.
    routing_decision_uri = f"atlas:routing/{invocation_id}"
    return {
        "uri": routing_decision_uri,
        "routingDecision": {
            "uri": routing_decision_uri,
            "selectedRoute": "ROUTE_ADVISOR_QUEUE",
        },
        "provenance": {
            "generatedBy": "referral-orchestrator",
            "generatedAtTime": None,
        },
    }


def _resolve_ask_graph(args: Dict, persona: str) -> Dict:
    """#2 Ask-the-graph — invoke nl-to-sparql-agent DIRECTLY by ARN (template-bounded
    NL->SPARQL). Maps the agent's {status, sparql, result, provenance} to NlQueryResult.
    Honest pass-through: no_template_match / execution_error are surfaced as-is with empty
    rows — never a fabricated answer."""
    question = args.get("question", "")
    if not NL_TO_SPARQL_ARN:
        return {"status": "execution_error", "sparql": None, "result": [],
                "templateId": None, "executionTimeMs": None}
    try:
        r = _invoke_agentcore(NL_TO_SPARQL_ARN,
                              {"question": question, "persona_claim": persona},
                              _current_bearer_token)
    except Exception as exc:
        logger.error(json.dumps({"event": "ask_graph_failed", "error": str(exc)}))
        return {"status": "execution_error", "sparql": None, "result": [],
                "templateId": None, "executionTimeMs": None}
    prov = r.get("provenance", {}) or {}
    return {
        "status": r.get("status", "execution_error"),
        "sparql": r.get("sparql") or None,
        # AWSJSON: AppSync serializes a JSON-typed field from a Python list/dict directly.
        "result": r.get("result", []),
        "templateId": prov.get("template_id") or None,
        "executionTimeMs": prov.get("execution_time_ms"),
    }


def _resolve_converse(args: Dict, persona: str) -> Dict:
    """#5 wealth conversation — invoke conversational-context-manager DIRECTLY by ARN.
    It wraps nl-to-sparql-agent (same templates as askGraph) and is single-turn (its
    Memory no-ops), so context_used.prior_turns is always 0 — surfaced as priorTurns.
    Honest pass-through: no_template_match / errors are returned as-is, never fabricated."""
    question = args.get("question", "")
    session_id = args.get("sessionId", "")
    if not CONVERSATIONAL_ARN:
        return {"status": "query_error", "sparql": None, "result": [], "priorTurns": 0}
    try:
        r = _invoke_agentcore(CONVERSATIONAL_ARN,
                              {"question": question, "session_id": session_id,
                               "persona_claim": persona},
                              _current_bearer_token)
    except Exception as exc:
        logger.error(json.dumps({"event": "converse_failed", "error": str(exc)}))
        return {"status": "query_error", "sparql": None, "result": [], "priorTurns": 0}
    ctx = r.get("context_used", {}) or {}
    return {
        "status": r.get("status", "query_error"),
        "sparql": r.get("sparql") or None,
        "result": r.get("result", []),
        "priorTurns": ctx.get("prior_turns", 0),
    }


def _resolve_draft_rationale(args: Dict, persona: str) -> Dict:
    """#3 Draft-rationale — invoke referral-rationale-drafter DIRECTLY by ARN. The draft is
    grounded in the household's REAL signals (signal_uris); always probabilistic +
    requires-review. Maps {status, draft_narrative, ...} to DraftResult."""
    household_uri = args.get("householdUri", "")
    signal_uris = args.get("signalUris", []) or []
    if not DRAFTER_ARN:
        return {"status": "generation_failed", "draftNarrative": None,
                "isProbabilistic": True, "requiresHumanReview": True, "generatedBy": None}
    try:
        r = _invoke_agentcore(DRAFTER_ARN,
                              {"household_uri": household_uri, "signal_uris": signal_uris,
                               "persona_claim": persona},
                              _current_bearer_token)
    except Exception as exc:
        logger.error(json.dumps({"event": "draft_rationale_failed", "error": str(exc)}))
        return {"status": "generation_failed", "draftNarrative": None,
                "isProbabilistic": True, "requiresHumanReview": True, "generatedBy": None}
    prov = r.get("provenance", {}) or {}
    return {
        "status": r.get("status", "generation_failed"),
        "draftNarrative": r.get("draft_narrative") or None,
        # The agent hardcodes these true; preserve them (never auto-route).
        "isProbabilistic": bool(r.get("is_probabilistic", True)),
        "requiresHumanReview": bool(r.get("requires_human_review", True)),
        "generatedBy": prov.get("model_id") or None,
    }


def _resolve_suggested_questions() -> list:
    """The questions Ask-the-graph can answer — read live from the SAME ground-truth.yaml
    the agent matches against (zero drift). Parses the `question:` lines with the stdlib
    (no PyYAML dependency in the resolver bundle). READ only — never edits the WS1 file."""
    if not GROUND_TRUTH_S3_URI:
        return []
    try:
        without_scheme = GROUND_TRUTH_S3_URI[len("s3://"):]
        bucket, _, key = without_scheme.partition("/")
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    except Exception as exc:
        logger.error(json.dumps({"event": "suggested_questions_failed", "error": str(exc)}))
        return []
    # Each template is a `  - question: "..."` line. Extract the quoted text in order.
    questions = re.findall(r'^\s*-\s*question:\s*"(.+?)"\s*$', body, flags=re.MULTILINE)
    return questions


def _invoke_registry(operation: str, payload: Dict) -> Dict:
    """Invoke atlas-registry-mcp via AgentCore HTTP."""
    result = _invoke_agentcore(REGISTRY_MCP_ARN, {"operation": operation, **payload}, _current_bearer_token)
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "Registry MCP error"))
    return result
