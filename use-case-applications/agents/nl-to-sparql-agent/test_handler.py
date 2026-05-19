"""
Unit tests for nl-to-sparql-agent Lambda handler.

Tests use real shared module imports (atlas_sparql.validate runs for real).
Bedrock embedding calls and Lambda invocations are mocked.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

# Set environment variables before import
os.environ.setdefault("GROUND_TRUTH_S3_URI", "")
os.environ.setdefault("PREFIXES_S3_URI", "")
os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")
os.environ.setdefault("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

import handler as handler_module
from handler import handler


# Reset template cache between tests
@pytest.fixture(autouse=True)
def reset_caches():
    handler_module._templates = None
    handler_module._prefix_preamble = None
    yield


def _mock_embedding(text: str) -> list:
    """Generate a deterministic fake embedding based on text hash."""
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()
    # Create a 256-dim vector from the hash (repeating)
    return [int(h[i % 32], 16) / 15.0 for i in range(256)]


class TestHappyPath:
    """Tests for successful question-to-SPARQL translation."""

    @patch("handler.boto3")
    def test_matching_question_returns_sparql(self, mock_boto3):
        """A question matching a template returns the template's SPARQL."""
        # Mock Bedrock embedding calls to return high-similarity vectors
        mock_bedrock = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "lambda":
                return mock_lambda
            elif service_name == "s3":
                return MagicMock()
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # Make embeddings return identical vectors for matching
        embedding_vector = [0.5] * 256
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({"embedding": embedding_vector}).encode()))
        }

        # Mock SPARQL MCP response
        sparql_result = json.dumps({"status": "success", "rows": [{"customer": "atlas:cust/001"}]}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        event = {
            "question": "Which customers have generated a wealth signal in the last 90 days?",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["sparql"] != ""
        assert "provenance" in result
        assert result["provenance"]["template_id"] != ""
        assert "invocation_id" in result

    @patch("handler.boto3")
    def test_determinism_same_question_same_sparql(self, mock_boto3):
        """Running the same question multiple times produces identical SPARQL (determinism check)."""
        mock_bedrock = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        embedding_vector = [0.5] * 256
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({"embedding": embedding_vector}).encode()))
        }

        sparql_result = json.dumps({"status": "success", "rows": []}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=sparql_result))
        }

        event = {
            "question": "Which customers have no wealth advisor assigned?",
            "persona_claim": "atlas-consumer-banker",
        }

        # Run 3 times
        results = []
        for _ in range(3):
            handler_module._templates = None  # Reset to force reload
            r = handler(event, None)
            if r["status"] == "success":
                results.append(r["sparql"])

        # All successful runs should produce identical SPARQL
        if len(results) > 1:
            assert all(s == results[0] for s in results), "Determinism violated: different SPARQL for same question"


class TestInputValidation:
    """Tests for input validation failures."""

    def test_missing_question_rejected(self):
        """Handler rejects event without question field."""
        event = {"persona_claim": "atlas-consumer-banker"}

        result = handler(event, None)

        assert result["status"] == "no_template_match"
        assert result["sparql"] == ""

    def test_invalid_persona_rejected(self):
        """Handler rejects invalid persona_claim."""
        event = {
            "question": "Which customers?",
            "persona_claim": "atlas-hacker",
        }

        result = handler(event, None)

        assert result["status"] == "no_template_match"

    def test_question_too_long_rejected(self):
        """Handler rejects questions exceeding 500 characters."""
        event = {
            "question": "x" * 501,
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "no_template_match"


class TestDownstreamFailures:
    """Tests for downstream dependency failures."""

    @patch("handler.boto3")
    def test_bedrock_failure_returns_error(self, mock_boto3):
        """When Bedrock embedding call fails, handler returns execution_error."""
        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock throttled")

        mock_boto3.client.side_effect = lambda svc, **kw: mock_bedrock if svc == "bedrock-runtime" else MagicMock()

        event = {
            "question": "Which customers have a wealth signal?",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "execution_error"

    @patch("handler.boto3")
    def test_sparql_mcp_failure_returns_execution_error(self, mock_boto3):
        """When atlas-sparql-mcp returns error, handler surfaces it."""
        mock_bedrock = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # Embedding succeeds
        embedding_vector = [0.5] * 256
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({"embedding": embedding_vector}).encode()))
        }

        # SPARQL MCP fails
        error_payload = json.dumps({"status": "error", "message": "Neptune connection refused"}).encode()
        mock_lambda.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=error_payload))
        }

        event = {
            "question": "Which customers have a wealth signal?",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "execution_error"
        assert result["sparql"] != ""  # SPARQL was generated before execution failed

    @patch("handler.boto3")
    def test_no_template_match_returns_graceful_refusal(self, mock_boto3):
        """When no template matches, handler returns no_template_match (not an exception)."""
        mock_bedrock = MagicMock()

        mock_boto3.client.side_effect = lambda svc, **kw: mock_bedrock if svc == "bedrock-runtime" else MagicMock()

        # Return very different embeddings so nothing matches
        call_count = [0]

        def varying_embedding(*args, **kwargs):
            call_count[0] += 1
            vec = [float(call_count[0]) / 100.0] * 256
            return {"body": MagicMock(read=MagicMock(return_value=json.dumps({"embedding": vec}).encode()))}

        mock_bedrock.invoke_model.side_effect = varying_embedding

        event = {
            "question": "What is the meaning of life?",  # Not a banking question
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "no_template_match"
        assert result["sparql"] == ""
        assert result["result"] == []
