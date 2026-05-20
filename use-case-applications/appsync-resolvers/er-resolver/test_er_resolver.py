"""
Unit tests for the Entity Resolution AppSync resolver.
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

os.environ.setdefault("ER_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-er-mcp")
os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")

from er_resolver import handler


class TestResolveEntity:

    @patch("er_resolver.boto3")
    def test_resolves_source_id_to_customer(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        # First call: ER lookup returns canonical URI
        er_response = json.dumps({"status": "success", "canonical_uri": "atlas:cust/9c2a1e"}).encode()
        # Second call: SPARQL fetch returns customer data
        sparql_response = json.dumps({"status": "success", "rows": [{"customerId": "CUST-9C2A1E", "label": "Anjali Patel"}]}).encode()

        mock_lambda.invoke.side_effect = [
            {"Payload": MagicMock(read=MagicMock(return_value=er_response))},
            {"Payload": MagicMock(read=MagicMock(return_value=sparql_response))},
        ]

        event = {
            "info": {"fieldName": "resolveEntity"},
            "arguments": {"sourceSystem": "SAP_KNA1", "sourceId": "4711837"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)

        assert result["uri"] == "atlas:cust/9c2a1e"
        assert result["customerId"] == "CUST-9C2A1E"
        assert result["label"] == "Anjali Patel"

    @patch("er_resolver.boto3")
    def test_returns_none_when_no_match(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        er_response = json.dumps({"status": "no_match", "canonical_uri": ""}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=er_response))}

        event = {
            "info": {"fieldName": "resolveEntity"},
            "arguments": {"sourceSystem": "UNKNOWN", "sourceId": "000"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)
        assert result is None

    @patch("er_resolver.boto3")
    def test_er_failure_returns_none(self, mock_boto3):
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        er_response = json.dumps({"status": "error", "message": "ER unavailable"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=er_response))}

        event = {
            "info": {"fieldName": "resolveEntity"},
            "arguments": {"sourceSystem": "SAP", "sourceId": "123"},
            "identity": {"claims": {"custom:persona": "atlas-consumer-banker"}},
        }

        result = handler(event, None)
        assert result is None
