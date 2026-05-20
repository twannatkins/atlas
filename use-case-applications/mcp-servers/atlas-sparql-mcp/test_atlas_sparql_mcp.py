"""
Unit tests for atlas-sparql-mcp Lambda handler.

Tests use real shared module imports (atlas_sparql.validate runs for real)
and mock only external AWS services (Neptune HTTP, Lambda invocations).
"""

from __future__ import annotations

import json
import os
import sys

# Ensure this directory is first on sys.path for handler import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import patch, MagicMock

import pytest

# Add shared modules to path so atlas_sparql imports work for real
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

# Set required environment variables before importing handler
os.environ.setdefault("NEPTUNE_SLGD_ENDPOINT", "test-cluster.us-east-1.neptune.amazonaws.com")
os.environ.setdefault("NEPTUNE_LGD_ENDPOINT", "test-lgd.us-east-1.neptune.amazonaws.com")
os.environ.setdefault("ONTOP_ECS_ENDPOINT", "http://ontop.local:8080")
os.environ.setdefault("SHACL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-shacl-mcp")

from atlas_sparql_mcp import handler


class TestQueryOperation:
    """Tests for the query operation."""

    @patch("atlas_sparql_mcp._sigv4_headers", return_value={"Authorization": "AWS4-HMAC-SHA256 ..."})
    @patch("atlas_sparql_mcp.http_requests")
    def test_happy_path_query(self, mock_requests, mock_sigv4):
        """A valid SELECT query returns parsed rows."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "head": {"vars": ["customer", "name"]},
            "results": {
                "bindings": [
                    {"customer": {"value": "atlas:cust/001"}, "name": {"value": "Alice"}},
                    {"customer": {"value": "atlas:cust/002"}, "name": {"value": "Bob"}},
                ]
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        event = {
            "operation": "query",
            "sparql": "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nSELECT ?customer ?name WHERE { ?customer a atlas:Customer ; rdfs:label ?name }",
            "persona_claim": "atlas-consumer-banker",
            "graph_tier": "slgd",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["rows"]) == 2
        assert result["rows"][0]["customer"] == "atlas:cust/001"
        assert "execution_time_ms" in result
        assert "invocation_id" in result

    def test_missing_persona_claim_rejected(self):
        """Query without persona_claim returns validation error."""
        event = {
            "operation": "query",
            "sparql": "SELECT ?s WHERE { ?s ?p ?o }",
            # persona_claim missing
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "persona_claim" in result["message"]

    def test_invalid_sparql_rejected(self):
        """Malformed SPARQL is caught by atlas_sparql.validate()."""
        event = {
            "operation": "query",
            "sparql": "SELEKT ?s WERE { ?s ?p ?o }",  # intentional typos
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "sparql_validation_error"

    @patch("atlas_sparql_mcp._sigv4_headers", return_value={"Authorization": "AWS4-HMAC-SHA256 ..."})
    @patch("atlas_sparql_mcp.http_requests")
    def test_neptune_failure_returns_execution_error(self, mock_requests, mock_sigv4):
        """When Neptune returns an error, the handler surfaces it cleanly."""
        mock_requests.get.side_effect = Exception("Connection refused")

        event = {
            "operation": "query",
            "sparql": "SELECT ?s WHERE { ?s ?p ?o }",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "execution_error"
        assert "Connection refused" in result["message"]


class TestUpdateOperation:
    """Tests for the update operation."""

    @patch("atlas_sparql_mcp._sigv4_headers", return_value={"Authorization": "AWS4-HMAC-SHA256 ..."})
    @patch("atlas_sparql_mcp.http_requests")
    def test_happy_path_update(self, mock_requests, mock_sigv4):
        """A valid UPDATE with required prefixes succeeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        sparql = (
            "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
            "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
            "INSERT DATA { atlas:cust/001 atlas:hasScore atlas:score/001 }"
        )

        event = {
            "operation": "update",
            "sparql": sparql,
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "success"

    def test_update_without_prefixes_rejected(self):
        """UPDATE missing required atlas:/prov: prefixes is rejected."""
        event = {
            "operation": "update",
            "sparql": "INSERT DATA { <x> <y> <z> }",
            "persona_claim": "atlas-ontology-steward",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "sparql_validation_error"
        assert "prefix" in result["message"].lower()


class TestConstructAndValidate:
    """Tests for the construct_and_validate operation."""

    @patch("atlas_sparql_mcp.boto3")
    @patch("atlas_sparql_mcp._sigv4_headers", return_value={"Authorization": "AWS4-HMAC-SHA256 ..."})
    @patch("atlas_sparql_mcp.http_requests")
    def test_happy_path_construct_and_validate(self, mock_requests, mock_sigv4, mock_boto3):
        """CONSTRUCT + SHACL validation returns triples and report."""
        # Mock CONSTRUCT HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "head": {"vars": ["s", "p", "o"]},
            "results": {
                "bindings": [
                    {"s": {"value": "atlas:sig/001"}, "p": {"value": "rdf:type"}, "o": {"value": "atlas:WealthSignal"}},
                ]
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        # Mock SHACL MCP Lambda invocation
        mock_lambda_client = MagicMock()
        mock_boto3.client.return_value = mock_lambda_client
        shacl_payload = json.dumps({"conforms": True, "report": {}}).encode()
        mock_lambda_client.invoke.return_value = {
            "Payload": MagicMock(read=MagicMock(return_value=shacl_payload))
        }

        event = {
            "operation": "construct_and_validate",
            "construct_sparql": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
            "shape_uri": "atlas:WealthSignalTypeShape",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert "triples_minted" in result
        assert "validation_report" in result

    def test_missing_shape_uri_rejected(self):
        """construct_and_validate without shape_uri returns validation error."""
        event = {
            "operation": "construct_and_validate",
            "construct_sparql": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
            # shape_uri missing
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "shape_uri" in result["message"]


class TestInvalidOperation:
    """Tests for unknown operations."""

    def test_unknown_operation_rejected(self):
        """An unrecognized operation returns an error."""
        event = {"operation": "delete_everything"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "invalid_operation"
