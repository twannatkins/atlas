"""
Unit tests for household-traverser Lambda handler.

Tests use real shared module imports. Mocks atlas-sparql-mcp Lambda calls.
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

from handler import handler


class TestHappyPath:
    """Tests for successful household traversal."""

    @patch("handler.boto3")
    def test_traversal_returns_nodes(self, mock_boto3):
        """A valid household URI returns 1-hop neighbor nodes."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        sparql_result = json.dumps({
            "status": "success",
            "rows": [
                {"uri": "atlas:cust/001", "type": "atlas:Customer", "label": "Anjali Patel", "relationship": "atlas:hasMember"},
                {"uri": "atlas:acct/002", "type": "atlas:Account", "label": "Checking 4421", "relationship": "atlas:hasAccount"},
            ],
        }).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["nodes"]) == 2
        assert result["nodes"][0]["uri"] == "atlas:cust/001"
        assert result["nodes"][0]["type"] == "atlas:Customer"
        assert result["nodes"][0]["relationship"] == "atlas:hasMember"
        assert "execution_time_ms" in result

    @patch("handler.boto3")
    def test_empty_household_returns_not_found(self, mock_boto3):
        """A household with no neighbors returns not_found."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        sparql_result = json.dumps({"status": "success", "rows": []}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        event = {
            "household_uri": "atlas:hh/nonexistent",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "not_found"
        assert result["nodes"] == []


class TestInputValidation:
    """Tests for input validation failures."""

    def test_missing_household_uri_rejected(self):
        """Handler rejects event without household_uri."""
        event = {"persona_claim": "atlas-consumer-banker"}

        result = handler(event, None)

        assert result["status"] == "query_error"
        assert "household_uri" in result.get("error_message", "")

    def test_invalid_persona_rejected(self):
        """Handler rejects invalid persona_claim."""
        event = {
            "household_uri": "atlas:hh/001",
            "persona_claim": "atlas-hacker",
        }

        result = handler(event, None)

        assert result["status"] == "query_error"


class TestDownstreamFailures:
    """Tests for downstream dependency failures."""

    @patch("handler.boto3")
    def test_sparql_mcp_failure(self, mock_boto3):
        """When atlas-sparql-mcp fails, handler returns query_error."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        error_payload = json.dumps({"status": "error", "message": "Neptune timeout"}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=error_payload))
        }

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "query_error"
        assert "SPARQL execution failed" in result.get("error_message", "")
