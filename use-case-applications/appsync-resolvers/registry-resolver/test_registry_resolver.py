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

from registry_resolver import handler


class TestCapabilitiesResolver:
    """capabilities resolves via _invoke_registry -> _invoke_agentcore (the AgentCore HTTP/
    SigV4 transport). The tests mock _invoke_registry, the single seam that returns the
    registry-mcp payload, so they assert the real mapping the live resolver performs (not
    the obsolete lambda.invoke/Payload SDK path)."""

    @patch("registry_resolver._invoke_registry")
    def test_returns_capabilities_for_persona(self, mock_invoke_registry):
        mock_invoke_registry.return_value = {
            "status": "success",
            "agents": [
                {"agentName": "nl-to-sparql-agent", "posture": "deterministic-audited",
                 "registryMetadata": {"display_name": "Ask the graph", "display_icon": "search", "capability_tag": "deterministic", "phase": 1}},
            ],
            "mcp_servers": [],
        }

        event = {
            "info": {"fieldName": "capabilities"},
            "arguments": {"personaClaim": "atlas-consumer-banker"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)

        # The resolver invoked the registry with the list_capabilities op + persona.
        mock_invoke_registry.assert_called_once()
        assert mock_invoke_registry.call_args[0][0] == "list_capabilities"
        assert len(result) == 1
        assert result[0]["name"] == "nl-to-sparql-agent"
        assert result[0]["displayName"] == "Ask the graph"

    @patch("registry_resolver._invoke_registry")
    def test_registry_failure_raises(self, mock_invoke_registry):
        # _invoke_registry raises on an error status from the MCP (its real contract);
        # the resolver propagates it rather than returning a fabricated palette.
        mock_invoke_registry.side_effect = RuntimeError("service unavailable")

        event = {
            "info": {"fieldName": "capabilities"},
            "arguments": {"personaClaim": "atlas-consumer-banker"},
            "identity": {"claims": {}},
        }

        with pytest.raises(RuntimeError, match="service unavailable"):
            handler(event, None)


class TestRouteReferralResolver:
    """routeReferral starts the referral-orchestrator Step Functions execution directly
    (stepfunctions.start_execution) — NOT the old registry invoke path. The test mocks
    boto3's stepfunctions client and asserts the real conformant route."""

    @patch("registry_resolver.boto3")
    @patch("registry_resolver.STATE_MACHINE_ARN",
           "arn:aws:states:us-east-1:123456789012:stateMachine:atlas-referral-orchestrator")
    def test_starts_orchestrator_execution(self, mock_boto3):
        # Patch the module global STATE_MACHINE_ARN directly (no reload — reloading would
        # rebind boto3 to the real client and defeat the mock). boto3 is mocked so no real
        # Step Functions call is made.
        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn

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

        # It started a Step Functions execution (the real transport), not a Lambda invoke.
        mock_boto3.client.assert_called_with("stepfunctions")
        mock_sfn.start_execution.assert_called_once()
        # The returned route is the SHACL-conformant enum value, not the old free string.
        assert result["routingDecision"]["selectedRoute"] == "ROUTE_ADVISOR_QUEUE"
        assert result["uri"].startswith("atlas:routing/")
