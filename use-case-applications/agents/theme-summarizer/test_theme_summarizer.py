"""
Unit tests for theme-summarizer Lambda handler.

Verifies probabilistic flags are always present and hardcoded.
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
os.environ.setdefault("BEDROCK_TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

from theme_summarizer import handler


class TestHappyPath:

    @patch("theme_summarizer.boto3")
    def test_summary_generated_with_flags(self, mock_boto3):
        """A successful summary always carries probabilistic flags."""
        mock_bedrock = MagicMock()
        mock_agentcore = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "bedrock-agentcore":
                return mock_agentcore
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # Mock SPARQL response with articles
        sparql_result = json.dumps({
            "status": "success",
            "rows": [
                {"article_uri": "article:001", "title": "Tech sector rally", "source": "Reuters"},
            ],
        }).encode()
        mock_agentcore.invoke_agent_runtime.return_value = {"response": MagicMock(read=MagicMock(return_value=sparql_result))}

        # Mock Bedrock response
        bedrock_response = json.dumps({
            "content": [{"text": "Tech sector shows continued momentum driven by AI adoption."}],
        }).encode()
        mock_bedrock.invoke_model.return_value = {"body": MagicMock(read=MagicMock(return_value=bedrock_response))}

        event = {"theme_uri": "atlas-part-2:theme/tech-rally", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "success"
        assert result["summary"] != ""
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True
        assert len(result["source_articles"]) > 0


class TestInputValidation:

    def test_missing_theme_uri_rejected(self):
        event = {"persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)
        assert result["status"] == "query_failed"
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True

    def test_invalid_persona_rejected(self):
        event = {"theme_uri": "atlas-part-2:theme/001", "persona_claim": "atlas-consumer-banker"}
        result = handler(event, None)
        assert result["status"] == "query_failed"


class TestDownstreamFailures:

    @patch("theme_summarizer.boto3")
    def test_bedrock_failure(self, mock_boto3):
        """When Bedrock fails, handler returns generation_failed with flags."""
        mock_bedrock = MagicMock()
        mock_agentcore = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-runtime":
                return mock_bedrock
            elif service_name == "bedrock-agentcore":
                return mock_agentcore
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        sparql_result = json.dumps({"status": "success", "rows": [{"title": "Article"}]}).encode()
        mock_agentcore.invoke_agent_runtime.return_value = {"response": MagicMock(read=MagicMock(return_value=sparql_result))}
        mock_bedrock.invoke_model.side_effect = Exception("Bedrock throttled")

        event = {"theme_uri": "atlas-part-2:theme/001", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "generation_failed"
        assert result["is_probabilistic"] is True
        assert result["requires_human_review"] is True

    @patch("theme_summarizer.boto3")
    def test_sparql_failure(self, mock_boto3):
        """When SPARQL MCP fails, handler returns query_failed."""
        mock_agentcore = MagicMock()
        mock_boto3.client.return_value = mock_agentcore

        error_payload = json.dumps({"status": "error", "message": "timeout"}).encode()
        mock_agentcore.invoke_agent_runtime.return_value = {"response": MagicMock(read=MagicMock(return_value=error_payload))}

        event = {"theme_uri": "atlas-part-2:theme/001", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "query_failed"
