"""
Unit tests for referral-rationale-drafter Lambda handler.

Tests use real shared module imports. Mocks Bedrock and Lambda calls.
Verifies that probabilistic flags are always present and hardcoded.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")
os.environ.setdefault("BEDROCK_TEXT_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
os.environ.setdefault("PROMPT_TEMPLATE_S3_URI", "")

import handler as handler_module
from handler import handler


@pytest.fixture(autouse=True)
def reset_caches():
    handler_module._prompt_template = None
    yield


class TestHappyPath:
    """Tests for successful rationale drafting."""

    @patch("handler.boto3")
    def test_draft_generated_with_probabilistic_flags(self, mock_boto3):
        """A successful draft always carries is_probabilistic=True and requires_human_review=True."""
        mock_bedrock = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # Mock SPARQL MCP responses for context queries
        sparql_result = json.dumps({
            "status": "success",
            "rows": [{"member": "atlas:cust/001", "memberType": "atlas:Customer", "label": "Anjali Patel"}],
        }).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        # Mock Bedrock response
        bedrock_response = json.dumps({
            "content": [{"text": "This household shows strong wealth-readiness signals including a large inbound wire."}],
        }).encode()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=bedrock_response))
        }

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/abc123"],
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["draft_narrative"] != ""
        # Critical: probabilistic flags are always present and True
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True
        assert "provenance" in result
        assert result["provenance"]["model_id"] == "anthropic.claude-sonnet-4-20250514-v1:0"

    @patch("handler.boto3")
    def test_flags_present_even_on_error(self, mock_boto3):
        """Even on error, is_probabilistic and requires_human_review are present."""
        mock_boto3.client.side_effect = lambda svc, **kw: MagicMock()

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": [],  # Empty — will fail validation
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        # Flags are present regardless of status
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True


class TestInputValidation:
    """Tests for input validation failures."""

    def test_missing_household_uri_rejected(self):
        """Handler rejects event without household_uri."""
        event = {
            "signal_uris": ["atlas:signal/001"],
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "context_query_failed"
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True

    def test_invalid_persona_rejected(self):
        """Only atlas-consumer-banker can invoke this agent."""
        event = {
            "household_uri": "atlas:hh/001",
            "signal_uris": ["atlas:signal/001"],
            "persona_claim": "atlas-wealth-advisor",  # Not allowed
        }

        result = handler(event, None)

        assert result["status"] == "context_query_failed"

    def test_missing_signal_uris_rejected(self):
        """Handler rejects event without signal_uris."""
        event = {
            "household_uri": "atlas:hh/001",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "context_query_failed"


class TestDownstreamFailures:
    """Tests for downstream dependency failures."""

    @patch("handler.boto3")
    def test_bedrock_failure_returns_generation_failed(self, mock_boto3):
        """When Bedrock fails, handler returns generation_failed."""
        mock_bedrock = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # SPARQL succeeds
        sparql_result = json.dumps({"status": "success", "rows": []}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        # Bedrock fails
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock throttled")

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "generation_failed"
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True

    @patch("handler.boto3")
    def test_sparql_mcp_failure_returns_context_query_failed(self, mock_boto3):
        """When SPARQL MCP fails, handler returns context_query_failed."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        error_payload = json.dumps({"status": "error", "message": "Neptune timeout"}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=error_payload))
        }

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "context_query_failed"
