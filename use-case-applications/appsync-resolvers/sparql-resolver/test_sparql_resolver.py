"""
Unit tests for the SPARQL AppSync resolver.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")

from sparql_resolver import handler


def _mock_sparql_response(rows):
    payload = json.dumps({"status": "success", "rows": rows}).encode()
    return {"Payload": MagicMock(read=MagicMock(return_value=payload))}


class TestCustomerResolver:

    @patch("sparql_resolver.boto3")
    def test_resolves_customer_by_uri(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"customerId": "CUST-001", "label": "Anjali Patel"},
        ])

        event = {
            "info": {"fieldName": "customer"},
            "arguments": {"uri": "atlas:cust/9c2a1e"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)

        assert result["uri"] == "atlas:cust/9c2a1e"
        assert result["customerId"] == "CUST-001"
        assert result["label"] == "Anjali Patel"

    @patch("sparql_resolver.boto3")
    def test_returns_none_for_missing_customer(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([])

        event = {
            "info": {"fieldName": "customer"},
            "arguments": {"uri": "atlas:cust/nonexistent"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)
        assert result is None

    @patch("sparql_resolver.boto3")
    def test_sparql_mcp_failure_raises(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        error_payload = json.dumps({"status": "error", "message": "timeout"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=error_payload))}

        event = {
            "info": {"fieldName": "customer"},
            "arguments": {"uri": "atlas:cust/001"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        with pytest.raises(RuntimeError, match="timeout"):
            handler(event, None)


class TestSearchCustomers:

    @patch("sparql_resolver.boto3")
    def test_returns_list(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"uri": "atlas:cust/001", "customerId": "C001", "label": "Alice"},
            {"uri": "atlas:cust/002", "customerId": "C002", "label": "Bob"},
        ])

        event = {
            "info": {"fieldName": "searchCustomers"},
            "arguments": {"query": "", "limit": 20},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)
        assert len(result) == 2
        assert result[0]["customerId"] == "C001"


class TestWealthSignals:

    @patch("sparql_resolver.boto3")
    def test_returns_signals_for_customer(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"uri": "atlas:sig/001", "signalType": "LargeInboundWireSignal", "strength": "strong", "signalDate": None},
        ])

        event = {
            "info": {"fieldName": "wealthSignals"},
            "arguments": {"customerUri": "atlas:cust/9c2a1e"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)
        assert len(result) == 1
        assert result[0]["signalType"] == "LargeInboundWireSignal"


class TestPersonaExtraction:

    @patch("sparql_resolver.boto3")
    def test_extracts_persona_from_custom_claim(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([])

        event = {
            "info": {"fieldName": "searchCustomers"},
            "arguments": {"limit": 5},
            "identity": {"claims": {"custom:persona": "atlas-bsa-analyst"}},
        }

        handler(event, None)

        # Verify the SPARQL MCP was called with the correct persona
        call_payload = json.loads(mock_lambda.invoke.call_args[1]["Payload"])
        assert call_payload["persona_claim"] == "atlas-bsa-analyst"
