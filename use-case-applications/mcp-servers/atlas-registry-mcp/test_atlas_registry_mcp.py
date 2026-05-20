"""
Unit tests for atlas-registry-mcp Lambda handler.

Mocks AWS Agent Registry (bedrock-agentcore) calls via patching boto3.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("REGISTRY_ENDPOINT", "https://agentcore.us-east-1.amazonaws.com")

from atlas_registry_mcp import handler


class TestListCapabilities:
    """Tests for the list_capabilities operation."""

    @patch("atlas_registry_mcp.boto3")
    def test_happy_path_list_capabilities(self, mock_boto3):
        """list_capabilities returns persona-filtered agents and MCP servers."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.list_agents.return_value = {
            "agents": [
                {"agentName": "nl-to-sparql-agent", "registryMetadata": {"discoverable_by": ["atlas-consumer-banker"]}},
                {"agentName": "theme-summarizer", "registryMetadata": {"discoverable_by": ["atlas-wealth-advisor"]}},
            ],
            "mcpServers": [
                {"mcpServerName": "atlas-sparql-mcp", "registryMetadata": {"discoverable_by": ["atlas-consumer-banker", "atlas-wealth-advisor"]}},
            ],
        }

        event = {
            "operation": "list_capabilities",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        # nl-to-sparql-agent is discoverable by consumer-banker
        assert any(a["agentName"] == "nl-to-sparql-agent" for a in result["agents"])

    def test_invalid_persona_rejected(self):
        """list_capabilities with invalid persona returns error."""
        event = {
            "operation": "list_capabilities",
            "persona_claim": "atlas-hacker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"

    @patch("atlas_registry_mcp.boto3")
    def test_registry_failure(self, mock_boto3):
        """When registry service fails, handler returns structured error."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.list_agents.side_effect = Exception("Service unavailable")

        event = {
            "operation": "list_capabilities",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "registry_error"


class TestGetAgent:
    """Tests for the get_agent operation."""

    @patch("atlas_registry_mcp.boto3")
    def test_happy_path_get_agent(self, mock_boto3):
        """get_agent returns the agent record."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.get_agent.return_value = {
            "agent": {"agentName": "nl-to-sparql-agent", "version": "1.0.0"},
        }

        event = {
            "operation": "get_agent",
            "agent_name": "nl-to-sparql-agent",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["agent"]["agentName"] == "nl-to-sparql-agent"

    def test_missing_agent_name_rejected(self):
        """get_agent without agent_name returns error."""
        event = {"operation": "get_agent"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "agent_name" in result["message"]


class TestGetMcpServer:
    """Tests for the get_mcp_server operation."""

    @patch("atlas_registry_mcp.boto3")
    def test_happy_path_get_mcp_server(self, mock_boto3):
        """get_mcp_server returns the MCP server record."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.get_agent.return_value = {
            "mcpServer": {"mcpServerName": "atlas-sparql-mcp", "version": "1.0.0"},
        }

        event = {
            "operation": "get_mcp_server",
            "mcp_name": "atlas-sparql-mcp",
        }

        result = handler(event, None)

        assert result["status"] == "success"

    def test_missing_mcp_name_rejected(self):
        """get_mcp_server without mcp_name returns error."""
        event = {"operation": "get_mcp_server"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "mcp_name" in result["message"]


class TestInvokeCapability:
    """Tests for the invoke_capability operation."""

    @patch("atlas_registry_mcp.boto3")
    def test_happy_path_invoke(self, mock_boto3):
        """invoke_capability proxies and returns result with audit URI."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_agent.return_value = {
            "result": {"answer": "42"},
            "auditRecordUri": "atlas:audit/abc123",
        }

        event = {
            "operation": "invoke_capability",
            "capability_uri": "nl-to-sparql-agent",
            "input_payload": {"question": "Which customers?"},
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["audit_record_uri"] == "atlas:audit/abc123"

    def test_missing_input_payload_rejected(self):
        """invoke_capability without input_payload returns error."""
        event = {
            "operation": "invoke_capability",
            "capability_uri": "nl-to-sparql-agent",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert "input_payload" in result["message"]


class TestInvalidOperation:
    def test_unknown_operation_rejected(self):
        event = {"operation": "unregister_all"}
        result = handler(event, None)
        assert result["status"] == "error"
        assert result["error_type"] == "invalid_operation"
