"""
atlas-registry-mcp — MCP server exposing the Agent Registry itself.

Exposes four operations:
  - list_capabilities: return agents/MCP servers discoverable by persona
  - get_agent: return registry record for a specific agent
  - get_mcp_server: return registry record for a specific MCP server
  - invoke_capability: proxy invocation through the registry's audit path

All operations are persona-scoped. Discovery is always claim-filtered.

Component class: DETERMINISTIC gateway — same persona + same registry state
= same discovery result.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
REGISTRY_ENDPOINT = os.environ.get("REGISTRY_ENDPOINT", "")

# ── Agent Registry integration ────────────────────────────────────────────────
#
# AWS Agent Registry is in Preview (as of 2026). This MCP supports two paths:
#
#   PATH A — AWS Agent Registry (when available and populated):
#     When ATLAS_REGISTRY_ID is set and the registry has APPROVED records, we
#     search the live registry via bedrock-agentcore-control.search_registry_records().
#     Each approved record carries a CUSTOM descriptor whose inlineContent JSON
#     embeds the ATLAS capability metadata (display_name, capability_tag, phase,
#     discoverable_by). This is the production-shape path that the workshop teaches.
#
#   PATH B — Embedded descriptor fallback (default / Preview workaround):
#     When Agent Registry is unavailable (not enabled, no records, or service
#     errors), we fall back to the descriptor JSON metadata embedded below.
#     The same metadata lives authoritatively in spec/04-aws-agent-registry/.
#     This path requires zero service dependencies and works in any account.
#
# To switch to PATH A:
#   1. Enable AWS Agent Registry in your account.
#   2. Run the registration script (spec/04-aws-agent-registry/register.py) to
#      publish and approve ATLAS records in a registry named "atlas-workshop-2".
#   3. Set the ATLAS_REGISTRY_ID env var on this runtime (the registry's 12-char ID).
#   The MCP will automatically prefer PATH A when ATLAS_REGISTRY_ID is present
#   and the registry returns records; it falls back to PATH B otherwise.

ATLAS_REGISTRY_ID = os.environ.get("ATLAS_REGISTRY_ID", "")

# Embedded capability descriptors — PATH B fallback.
# Mirrors the JSON files in spec/04-aws-agent-registry/agents/ and mcp-servers/.
# Update here when those descriptors change.
_CAPABILITIES_FALLBACK = [
    {"name": "household-traverser",           "displayName": "Traverse household",              "displayIcon": "affiliate",   "posture": "read",      "capabilityTag": "deterministic",  "phase": 1, "discoverable_by": ["atlas-consumer-banker", "atlas-wealth-advisor", "atlas-bsa-analyst", "atlas-ontology-steward"]},
    {"name": "nl-to-sparql-agent",            "displayName": "Ask the graph",                   "displayIcon": "search",      "posture": "read",      "capabilityTag": "deterministic",  "phase": 1, "discoverable_by": ["atlas-consumer-banker", "atlas-wealth-advisor", "atlas-bsa-analyst", "atlas-ontology-steward"]},
    {"name": "referral-orchestrator",         "displayName": "Route to advisor",                "displayIcon": "route",       "posture": "write",     "capabilityTag": "workflow",       "phase": 1, "discoverable_by": ["atlas-consumer-banker"]},
    {"name": "referral-rationale-drafter",    "displayName": "Draft referral rationale",        "displayIcon": "messages",    "posture": "generate",  "capabilityTag": "human-in-loop",  "phase": 1, "discoverable_by": ["atlas-consumer-banker"]},
    {"name": "wealth-signal-detector",        "displayName": "Detect wealth signals",           "displayIcon": "radar",       "posture": "read",      "capabilityTag": "deterministic",  "phase": 1, "discoverable_by": ["atlas-consumer-banker", "atlas-wealth-advisor", "atlas-ontology-steward"]},
    {"name": "behavioral-signal-agent",       "displayName": "Detect behavioral signals",       "displayIcon": "activity",    "posture": "read",      "capabilityTag": "deterministic",  "phase": 2, "discoverable_by": ["atlas-wealth-advisor"]},
    {"name": "conversational-context-manager","displayName": "Ask the graph (conversational)",  "displayIcon": "message-2",   "posture": "read",      "capabilityTag": "memory-backed",  "phase": 2, "discoverable_by": ["atlas-wealth-advisor"]},
    {"name": "theme-summarizer",              "displayName": "Summarize theme",                 "displayIcon": "newspaper",   "posture": "generate",  "capabilityTag": "informational",  "phase": 2, "discoverable_by": ["atlas-wealth-advisor"]},
]


def _list_capabilities_from_registry(persona_claim: str) -> list:
    """PATH A — query AWS Agent Registry for approved ATLAS capability records.

    Searches the registry for records whose CUSTOM descriptor inlineContent carries
    a discoverable_by list that includes the given persona. Falls back to an empty
    list (triggering PATH B) on any error, including service unavailability.
    """
    if not ATLAS_REGISTRY_ID:
        return []
    try:
        import boto3 as _boto3
        client = _boto3.client("bedrock-agentcore-control")
        response = client.search_registry_records(
            registryId=ATLAS_REGISTRY_ID,
            search_query=f"ATLAS capabilities for persona {persona_claim}",
            max_results=20,
        )
        capabilities = []
        for record in response.get("registryRecordSummaries", []):
            try:
                descriptor_content = record.get("descriptors", {}).get("custom", {}).get("inlineContent", "{}")
                meta = json.loads(descriptor_content)
                discoverable_by = meta.get("discoverable_by", [])
                if not discoverable_by or persona_claim in discoverable_by:
                    capabilities.append({
                        "name": record.get("name", ""),
                        "displayName": meta.get("display_name", record.get("description", "")),
                        "displayIcon": meta.get("display_icon", ""),
                        "posture": meta.get("posture", ""),
                        "capabilityTag": meta.get("capability_tag", ""),
                        "phase": meta.get("phase", 1),
                        "discoverable_by": discoverable_by,
                    })
            except Exception:
                continue
        return capabilities
    except Exception as exc:
        logger.info(json.dumps({
            "event": "registry_fallback",
            "reason": f"AWS Agent Registry unavailable or returned error: {exc}. Using embedded descriptors.",
        }))
        return []

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-bsa-analyst",
    "atlas-ontology-steward",
    "atlas-auditor",
]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for atlas-registry-mcp."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        operation = event.get("operation")
        if operation not in ("list_capabilities", "get_agent", "get_mcp_server", "invoke_capability"):
            return _error_response(
                invocation_id, start_time,
                "invalid_operation",
                f"Unknown operation: {operation}. Must be one of: list_capabilities, get_agent, get_mcp_server, invoke_capability",
            )

        if operation == "list_capabilities":
            return _handle_list_capabilities(event, invocation_id, start_time)
        elif operation == "get_agent":
            return _handle_get_agent(event, invocation_id, start_time)
        elif operation == "get_mcp_server":
            return _handle_get_mcp_server(event, invocation_id, start_time)
        else:
            return _handle_invoke_capability(event, invocation_id, start_time)

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "internal_error", str(exc))


def _handle_list_capabilities(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Return all agents and MCP servers discoverable by the given persona."""
    persona_claim = event.get("persona_claim")

    if not persona_claim or persona_claim not in VALID_PERSONAS:
        return _error_response(invocation_id, start_time, "validation_error", f"persona_claim must be one of: {VALID_PERSONAS}")

    try:
        # PATH A — try live AWS Agent Registry first (when ATLAS_REGISTRY_ID is set).
        # PATH B — fall back to embedded descriptors if registry is unavailable/empty.
        # The fallback is intentional for accounts where Agent Registry (Preview) is
        # not enabled or has not been populated via the registration script.
        agents = _list_capabilities_from_registry(persona_claim)
        if not agents:
            agents = _filter_by_persona(_CAPABILITIES_FALLBACK, persona_claim)
            logger.info(json.dumps({"event": "using_fallback_registry", "persona": persona_claim, "count": len(agents)}))
        else:
            logger.info(json.dumps({"event": "using_aws_registry", "persona": persona_claim, "count": len(agents)}))
        mcp_servers = []  # MCP servers are infrastructure; only agents surface in the UI palette

    except Exception as exc:
        return _error_response(invocation_id, start_time, "registry_error", f"Agent Registry query failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "list_capabilities")

    return {
        "status": "success",
        "agents": agents,
        "mcp_servers": mcp_servers,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_get_agent(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Return the registry record for a specific agent."""
    agent_name = event.get("agent_name")

    if not agent_name or not isinstance(agent_name, str):
        return _error_response(invocation_id, start_time, "validation_error", "agent_name is required")

    try:
        agentcore_client = boto3.client("bedrock-agentcore")
        response = agentcore_client.get_agent(agentName=agent_name)
        agent = response.get("agent", response)
    except Exception as exc:
        return _error_response(invocation_id, start_time, "registry_error", f"Failed to get agent: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, "success", "get_agent")

    return {
        "status": "success",
        "agent": agent,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_get_mcp_server(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Return the registry record for a specific MCP server."""
    mcp_name = event.get("mcp_name")

    if not mcp_name or not isinstance(mcp_name, str):
        return _error_response(invocation_id, start_time, "validation_error", "mcp_name is required")

    try:
        agentcore_client = boto3.client("bedrock-agentcore")
        response = agentcore_client.get_agent(agentName=mcp_name)
        mcp_server = response.get("mcpServer", response)
    except Exception as exc:
        return _error_response(invocation_id, start_time, "registry_error", f"Failed to get MCP server: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, "success", "get_mcp_server")

    return {
        "status": "success",
        "mcp_server": mcp_server,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _handle_invoke_capability(event: Dict[str, Any], invocation_id: str, start_time: float) -> Dict[str, Any]:
    """Proxy invocation through the registry's audit path."""
    capability_uri = event.get("capability_uri")
    input_payload = event.get("input_payload")
    persona_claim = event.get("persona_claim")

    if not capability_uri or not isinstance(capability_uri, str):
        return _error_response(invocation_id, start_time, "validation_error", "capability_uri is required")
    if not input_payload or not isinstance(input_payload, dict):
        return _error_response(invocation_id, start_time, "validation_error", "input_payload is required and must be an object")
    if not persona_claim or persona_claim not in VALID_PERSONAS:
        return _error_response(invocation_id, start_time, "validation_error", f"persona_claim must be one of: {VALID_PERSONAS}")

    try:
        agentcore_client = boto3.client("bedrock-agentcore")

        # Invoke through registry (adds audit trail)
        response = agentcore_client.invoke_agent(
            agentName=capability_uri,
            inputPayload=json.dumps(input_payload),
            personaClaim=persona_claim,
        )
        result = response.get("result", response)
        audit_record_uri = response.get("auditRecordUri", f"atlas:audit/{invocation_id}")

    except Exception as exc:
        return _error_response(invocation_id, start_time, "invocation_error", f"Capability invocation failed: {exc}")

    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "invoke_capability")

    return {
        "status": "success",
        "result": result,
        "audit_record_uri": audit_record_uri,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _filter_by_persona(items: list, persona_claim: str) -> list:
    """Filter capabilities by persona claim.

    Checks top-level discoverable_by (the _CAPABILITIES format) first,
    then falls back to registryMetadata.discoverable_by for legacy shapes.
    An empty or absent discoverable_by list means discoverable by all personas.
    """
    filtered = []
    for item in items:
        discoverable_by = (
            item.get("discoverable_by") or
            item.get("registryMetadata", {}).get("discoverable_by", [])
        )
        if not discoverable_by or persona_claim in discoverable_by:
            filtered.append(item)
    return filtered


def _error_response(invocation_id: str, start_time: float, error_type: str, message: str) -> Dict[str, Any]:
    """Build a structured error response."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "system", execution_time_ms, error_type, "error")
    return {
        "status": "error",
        "error_type": error_type,
        "message": message,
        "execution_time_ms": execution_time_ms,
        "invocation_id": invocation_id,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "service": "atlas-registry-mcp",
    }))
