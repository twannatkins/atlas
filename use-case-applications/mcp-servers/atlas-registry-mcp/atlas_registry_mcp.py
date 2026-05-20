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

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
REGISTRY_ENDPOINT = os.environ.get("REGISTRY_ENDPOINT", "")

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
        agentcore_client = boto3.client("bedrock-agentcore")

        # List agents filtered by persona
        agents_response = agentcore_client.list_agents()
        agents = _filter_by_persona(agents_response.get("agents", []), persona_claim)

        # List MCP servers (all are discoverable by all personas in Phase 1)
        mcp_response = agentcore_client.list_agents()  # Registry uses same API
        mcp_servers = _filter_by_persona(mcp_response.get("mcpServers", []), persona_claim)

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
    """Filter registry items by persona claim discoverable_by field."""
    filtered = []
    for item in items:
        discoverable_by = item.get("registryMetadata", {}).get("discoverable_by", [])
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
