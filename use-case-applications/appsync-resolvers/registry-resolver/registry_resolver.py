"""
AppSync resolver Lambda — handles registry and agent invocation queries.

Translates GraphQL capabilities query and mutations into atlas-registry-mcp
calls. Passes persona claim from Cognito JWT through to the registry for
persona-scoped discovery.

Handles: capabilities, routeReferral, detectSignals.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict

import urllib.parse
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGISTRY_MCP_ARN = os.environ.get("REGISTRY_MCP_ARN", "")

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
        elif field_name == "detectSignals":
            return _resolve_detect_signals(arguments, persona_claim)
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
    """Invoke referral-orchestrator through the registry audit path."""
    # Extract the originating banker from identity
    sub = identity.get("claims", {}).get("sub", args.get("originatingBankerId", ""))

    payload = {
        "household_uri": args["householdUri"],
        "signal_uris": args["signalUris"],
        "approved_rationale": args["approvedRationale"],
        "originating_banker_id": args.get("originatingBankerId", sub),
        "persona_claim": persona,
    }

    result = _invoke_registry("invoke_capability", {
        "capability_uri": "referral-orchestrator",
        "input_payload": payload,
        "persona_claim": persona,
    })

    inner = result.get("result", result)
    return {
        "uri": inner.get("routing_decision_uri", ""),
        "routingDecision": {
            "uri": inner.get("routing_decision_uri", ""),
            "selectedRoute": "route_to_advisor",
        },
        "provenance": {
            "generatedBy": "referral-orchestrator",
            "generatedAtTime": None,
        },
    }


def _resolve_detect_signals(args: Dict, persona: str) -> list:
    """Invoke wealth-signal-detector through the registry."""
    payload = {
        "target_uri": args["targetUri"],
        "signal_types": args.get("signalTypes"),
        "persona_claim": persona,
    }

    result = _invoke_registry("invoke_capability", {
        "capability_uri": "wealth-signal-detector",
        "input_payload": payload,
        "persona_claim": persona,
    })

    inner = result.get("result", result)
    signals = inner.get("signals_minted", [])
    return [
        {
            "uri": s.get("signal_uri", ""),
            "signalType": s.get("signal_type", ""),
            "strength": s.get("strength", ""),
            "signalDate": None,
            "provenance": {
                "validatedBy": "atlas:WealthSignalTypeShape",
                "derivedFrom": "wealth-signal-detector",
                "generatedBy": "wealth-signal-detector",
            },
        }
        for s in signals
    ]


def _invoke_registry(operation: str, payload: Dict) -> Dict:
    """Invoke atlas-registry-mcp via AgentCore HTTP."""
    result = _invoke_agentcore(REGISTRY_MCP_ARN, {"operation": operation, **payload}, _current_bearer_token)
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "Registry MCP error"))
    return result
