"""
Unit tests for conversational-context-manager Lambda handler.

Mocks AgentCore Memory and nl-to-sparql-agent Lambda calls.
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

os.environ.setdefault("NL_TO_SPARQL_AGENT_ARN", "arn:aws:lambda:us-east-1:123456789012:function:nl-to-sparql-agent")
os.environ.setdefault("AGENTCORE_MEMORY_NAMESPACE", "atlas-wealth-conv")

from handler import handler


class TestHappyPath:

    @patch("handler.boto3")
    def test_first_turn_no_prior_context(self, mock_boto3):
        """First turn in a session works without prior context."""
        mock_memory = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-agentcore":
                return mock_memory
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # No prior memory
        mock_memory.get_memory.side_effect = Exception("Not found")

        # nl-to-sparql-agent returns success
        nl_result = json.dumps({
            "status": "success",
            "sparql": "SELECT ?s WHERE { ?s ?p ?o }",
            "result": [{"s": "atlas:cust/001"}],
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=nl_result))}

        event = {
            "question": "Which customers have a wealth signal?",
            "session_id": "session-001",
            "persona_claim": "atlas-wealth-advisor",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["sparql"] != ""
        assert result["context_used"]["session_id"] == "session-001"
        assert result["context_used"]["prior_turns"] == 0

    @patch("handler.boto3")
    def test_follow_up_with_prior_context(self, mock_boto3):
        """Follow-up question uses prior context from memory."""
        mock_memory = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-agentcore":
                return mock_memory
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory

        # Prior context exists
        prior = json.dumps({"turns": [{"question": "Which customers?", "sparql": "SELECT ?s WHERE { ?s ?p ?o }", "result_count": 5}]})
        mock_memory.get_memory.return_value = {"content": prior}

        # nl-to-sparql-agent returns success
        nl_result = json.dumps({
            "status": "success",
            "sparql": "SELECT ?s WHERE { ?s ?p ?o . FILTER(?s IN (...)) }",
            "result": [{"s": "atlas:cust/002"}],
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=nl_result))}

        event = {
            "question": "Of those, which have no advisor?",
            "session_id": "session-001",
            "persona_claim": "atlas-wealth-advisor",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["context_used"]["prior_turns"] == 1


class TestInputValidation:

    def test_missing_question_rejected(self):
        event = {"session_id": "s1", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)
        assert result["status"] == "validation_error"

    def test_missing_session_id_rejected(self):
        event = {"question": "Which customers?", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)
        assert result["status"] == "validation_error"

    def test_invalid_persona_rejected(self):
        event = {"question": "Which?", "session_id": "s1", "persona_claim": "atlas-consumer-banker"}
        result = handler(event, None)
        assert result["status"] == "validation_error"


class TestDownstreamFailures:

    @patch("handler.boto3")
    def test_nl_to_sparql_failure(self, mock_boto3):
        """When nl-to-sparql-agent fails, handler returns query_error."""
        mock_memory = MagicMock()
        mock_lambda = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-agentcore":
                return mock_memory
            elif service_name == "lambda":
                return mock_lambda
            return MagicMock()

        mock_boto3.client.side_effect = client_factory
        mock_memory.get_memory.side_effect = Exception("Not found")
        mock_lambda.invoke.side_effect = Exception("Lambda timeout")

        event = {"question": "Which?", "session_id": "s1", "persona_claim": "atlas-wealth-advisor"}
        result = handler(event, None)

        assert result["status"] == "query_error"
