"""
Unit tests for atlas-fibo-mcp Lambda handler.

Mocks atlas-sparql-mcp Lambda invocations via patching boto3.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")

from atlas_fibo_mcp import handler


def _mock_sparql_response(rows):
    """Helper to create a mock Lambda invoke response."""
    payload = json.dumps({"status": "success", "rows": rows}).encode()
    return {"Payload": MagicMock(read=MagicMock(return_value=payload))}


class TestClassInfoOperation:
    """Tests for the class_info operation."""

    @patch("atlas_fibo_mcp.boto3")
    def test_happy_path_class_info(self, mock_boto3):
        """class_info returns label, comment, parents, and alignment."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"label": "Customer", "comment": "A banking customer", "parent": "fibo:Party", "alignment": "fibo:LegalPerson"},
        ])

        event = {
            "operation": "class_info",
            "class_uri": "https://github.com/your-org/atlas/ontology#Customer",
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["label"] == "Customer"
        assert result["comment"] == "A banking customer"
        assert "fibo:Party" in result["parents"]

    def test_missing_class_uri_rejected(self):
        """class_info without class_uri returns validation error."""
        event = {"operation": "class_info"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "class_uri" in result["message"]

    @patch("atlas_fibo_mcp.boto3")
    def test_sparql_mcp_failure(self, mock_boto3):
        """When atlas-sparql-mcp returns error, handler surfaces it."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        error_payload = json.dumps({"status": "error", "message": "Neptune timeout"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=error_payload))}

        event = {
            "operation": "class_info",
            "class_uri": "atlas:Customer",
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "sparql_error"


class TestListClassesOperation:
    """Tests for the list_classes operation."""

    @patch("atlas_fibo_mcp.boto3")
    def test_happy_path_list_classes(self, mock_boto3):
        """list_classes returns classes in the given namespace."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"class": "atlas:Customer", "label": "Customer"},
            {"class": "atlas:Account", "label": "Account"},
        ])

        event = {
            "operation": "list_classes",
            "namespace_prefix": "atlas",
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["classes"]) == 2

    def test_missing_namespace_prefix_rejected(self):
        """list_classes without namespace_prefix returns error."""
        event = {"operation": "list_classes"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "namespace_prefix" in result["message"]


class TestSubclassesOfOperation:
    """Tests for the subclasses_of operation."""

    @patch("atlas_fibo_mcp.boto3")
    def test_happy_path_subclasses(self, mock_boto3):
        """subclasses_of returns subclasses of the given class."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda
        mock_lambda.invoke.return_value = _mock_sparql_response([
            {"subclass": "atlas:WealthSignal", "label": "Wealth Signal"},
        ])

        event = {
            "operation": "subclasses_of",
            "class_uri": "atlas:Signal",
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["subclasses"]) == 1

    def test_missing_class_uri_rejected(self):
        """subclasses_of without class_uri returns error."""
        event = {"operation": "subclasses_of"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "class_uri" in result["message"]


class TestInvalidOperation:
    def test_unknown_operation_rejected(self):
        event = {"operation": "modify_ontology"}
        result = handler(event, None)
        assert result["status"] == "error"
        assert result["error_type"] == "invalid_operation"
