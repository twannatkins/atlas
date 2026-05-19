"""
Unit tests for behavioral-signal-agent Lambda handler.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure this directory is first on sys.path for handler import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")
os.environ.setdefault("SHACL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-shacl-mcp")

from handler import handler


class TestHappyPath:

    @patch("handler.boto3")
    def test_signals_detected(self, mock_boto3):
        """When CONSTRUCT returns triples, behavioral signals are minted."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        payload = json.dumps({
            "status": "success",
            "triples_minted": [{"s": "atlas:sig/001", "p": "rdf:type", "o": "atlas:WealthSignal"}],
            "validation_report": {"conforms": True},
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=payload))}

        event = {
            "customer_uri": "atlas:cust/9c2a1e",
            "persona_claim": "atlas-wealth-advisor",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["signals_minted"]) > 0

    @patch("handler.boto3")
    def test_no_signals_detected(self, mock_boto3):
        """When CONSTRUCT returns empty, status is no_signals_detected."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        payload = json.dumps({"status": "success", "triples_minted": [], "validation_report": {"conforms": True}}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=payload))}

        event = {"customer_uri": "atlas:cust/no-signals", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "no_signals_detected"


class TestInputValidation:

    def test_missing_customer_uri_rejected(self):
        event = {"persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)
        assert result["status"] == "validation_failed"

    def test_invalid_persona_rejected(self):
        event = {"customer_uri": "atlas:cust/001", "persona_claim": "atlas-consumer-banker"}
        result = handler(event, None)
        assert result["status"] == "validation_failed"


class TestDownstreamFailures:

    @patch("handler.boto3")
    def test_sparql_mcp_failure(self, mock_boto3):
        """When MCP fails, handler returns gracefully."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        error_payload = json.dumps({"status": "error", "message": "timeout"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=error_payload))}

        event = {"customer_uri": "atlas:cust/001", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "no_signals_detected"
