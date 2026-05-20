"""
Unit tests for the Registry AppSync resolver.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("REGISTRY_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-registry-mcp")

from handler import handler


class TestCapabilitiesResolver:

    @patch("handler.boto3")
    def test_returns_capabilities_for_persona(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        registry_response = json.dumps({
            "status": "success",
            "agents": [
                {"agentName": "nl-to-sparql-agent", "posture": "deterministic-audited",
                 "registryMetadata": {"display_name": "Ask the graph", "display_icon": "search", "capability_tag": "deterministic", "phase": 1}},
            ],
            "mcp_servers": [],
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=registry_response))}

        event = {
            "info": {"fieldName": "capabilities"},
            "arguments": {"personaClaim": "atlas-consumer-banker"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)

        assert len(result) == 1
        assert result[0]["name"] == "nl-to-sparql-agent"
        assert result[0]["displayName"] == "Ask the graph"

    @patch("handler.boto3")
    def test_registry_failure_raises(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        error_payload = json.dumps({"status": "error", "message": "service unavailable"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=error_payload))}

        event = {
            "info": {"fieldName": "capabilities"},
            "arguments": {"personaClaim": "atlas-consumer-banker"},
            "identity": {"claims": {}},
        }

        with pytest.raises(RuntimeError, match="service unavailable"):
            handler(event, None)


class TestRouteReferralResolver:

    @patch("handler.boto3")
    def test_invokes_orchestrator_through_registry(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        registry_response = json.dumps({
            "status": "success",
            "result": {
                "routing_decision_uri": "atlas:routing/abc123",
                "selected_advisor_uri": "atlas:advisor/001",
                "audit_record_uri": "atlas:audit/abc123",
            },
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=registry_response))}

        event = {
            "info": {"fieldName": "routeReferral"},
            "arguments": {
                "householdUri": "atlas:hh/9c2a1e",
                "signalUris": ["atlas:signal/001"],
                "approvedRationale": "Strong signals detected.",
                "originatingBankerId": "banker-001",
            },
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker", "sub": "banker-001"}},
        }

        result = handler(event, None)

        assert result["uri"] == "atlas:routing/abc123"
        assert result["routingDecision"]["selectedRoute"] == "route_to_advisor"


class TestDetectSignalsResolver:

    @patch("handler.boto3")
    def test_returns_minted_signals(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        registry_response = json.dumps({
            "status": "success",
            "result": {
                "signals_minted": [
                    {"signal_uri": "atlas:signal/new1", "signal_type": "LargeInboundWireSignal", "strength": "strong"},
                ],
            },
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=registry_response))}

        event = {
            "info": {"fieldName": "detectSignals"},
            "arguments": {"targetUri": "atlas:cust/9c2a1e"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)

        assert len(result) == 1
        assert result[0]["signalType"] == "LargeInboundWireSignal"
