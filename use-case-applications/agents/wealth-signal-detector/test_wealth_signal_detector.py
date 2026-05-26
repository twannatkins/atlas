"""
Unit tests for wealth-signal-detector Lambda handler.

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
os.environ.setdefault("SHACL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-shacl-mcp")
os.environ.setdefault("SIGNAL_QUERIES_S3_URI", "")

from wealth_signal_detector import handler


def _mock_construct_success(triples=None):
    """Helper to create a successful construct_and_validate response."""
    if triples is None:
        triples = [{"s": "atlas:sig/001", "p": "rdf:type", "o": "atlas:WealthSignal"}]
    payload = json.dumps({
        "status": "success",
        "triples_minted": triples,
        "validation_report": {"conforms": True},
    }).encode()
    return {"response": MagicMock(read=MagicMock(return_value=payload))}


def _mock_construct_empty():
    """Helper for construct that returns no triples (signal not detected)."""
    payload = json.dumps({
        "status": "success",
        "triples_minted": [],
        "validation_report": {"conforms": True},
    }).encode()
    return {"response": MagicMock(read=MagicMock(return_value=payload))}


class TestHappyPath:
    """Tests for successful signal detection."""

    @patch("wealth_signal_detector.boto3")
    def test_signals_detected(self, mock_boto3):
        """When CONSTRUCT returns triples, signals are minted."""
        mock_agentcore = MagicMock()
        mock_boto3.client.return_value = mock_agentcore
        mock_agentcore.invoke_agent_runtime.return_value = _mock_construct_success()

        event = {
            "target_uri": "atlas:cust/9c2a1e",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] in ("success", "partial")
        assert len(result["signals_minted"]) > 0
        assert all("signal_uri" in s for s in result["signals_minted"])
        assert all("signal_type" in s for s in result["signals_minted"])
        assert all("strength" in s for s in result["signals_minted"])
        assert "provenance" in result
        assert result["provenance"]["execution_time_ms"] >= 0

    @patch("wealth_signal_detector.boto3")
    def test_no_signals_detected(self, mock_boto3):
        """When CONSTRUCT returns empty, status is no_signals_detected."""
        mock_agentcore = MagicMock()
        mock_boto3.client.return_value = mock_agentcore
        mock_agentcore.invoke_agent_runtime.return_value = _mock_construct_empty()

        event = {
            "target_uri": "atlas:cust/no-signals",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "no_signals_detected"
        assert result["signals_minted"] == []

    @patch("wealth_signal_detector.boto3")
    def test_filtered_signal_types(self, mock_boto3):
        """When signal_types filter is provided, only those signals are checked."""
        mock_agentcore = MagicMock()
        mock_boto3.client.return_value = mock_agentcore
        mock_agentcore.invoke_agent_runtime.return_value = _mock_construct_success()

        event = {
            "target_uri": "atlas:cust/9c2a1e",
            "persona_claim": "atlas-consumer-banker",
            "signal_types": ["atlas-part-2:LargeInboundWireSignal"],
        }

        result = handler(event, None)

        # Only one signal type was requested
        assert result["status"] == "success"
        assert len(result["signals_minted"]) == 1
        assert result["signals_minted"][0]["signal_type"] == "atlas-part-2:LargeInboundWireSignal"


class TestInputValidation:
    """Tests for input validation failures."""

    def test_missing_target_uri_rejected(self):
        """Handler rejects event without target_uri."""
        event = {"persona_claim": "atlas-consumer-banker"}

        result = handler(event, None)

        assert result["status"] == "validation_failed"

    def test_invalid_persona_rejected(self):
        """Handler rejects invalid persona_claim."""
        event = {
            "target_uri": "atlas:cust/001",
            "persona_claim": "atlas-hacker",
        }

        result = handler(event, None)

        assert result["status"] == "validation_failed"


class TestDownstreamFailures:
    """Tests for downstream dependency failures."""

    @patch("wealth_signal_detector.boto3")
    def test_sparql_mcp_failure(self, mock_boto3):
        """When atlas-sparql-mcp fails, handler returns gracefully."""
        mock_agentcore = MagicMock()
        mock_boto3.client.return_value = mock_agentcore

        error_payload = json.dumps({"status": "error", "message": "Neptune timeout"}).encode()
        mock_agentcore.invoke_agent_runtime.return_value = {
            "response": MagicMock(read=MagicMock(return_value=error_payload))
        }

        event = {
            "target_uri": "atlas:cust/9c2a1e",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        # Should not crash — returns no_signals_detected or validation_failed
        assert result["status"] in ("no_signals_detected", "validation_failed")
        assert result["signals_minted"] == []
