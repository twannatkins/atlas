"""
Unit tests for atlas-er-mcp Lambda handler.

Mocks AWS Entity Resolution calls via patching boto3.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure this directory is first on sys.path for handler import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("ER_WORKFLOW_NAME", "atlas-test-workflow")

from handler import handler


class TestLookupOperation:
    """Tests for the lookup operation."""

    @patch("handler.boto3")
    def test_happy_path_lookup(self, mock_boto3):
        """A valid lookup returns canonical URI and confidence."""
        mock_er_client = MagicMock()
        mock_boto3.client.return_value = mock_er_client
        mock_er_client.get_match_id.return_value = {
            "matchId": "9c2a1e",
            "confidenceScore": 0.98,
        }

        event = {
            "operation": "lookup",
            "source_system": "SAP_KNA1",
            "source_id": "4711837",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["canonical_uri"] == "atlas:entity/9c2a1e"
        assert result["match_confidence"] == 0.98
        assert "execution_time_ms" in result

    @patch("handler.boto3")
    def test_lookup_no_match(self, mock_boto3):
        """When ER returns no match, status is no_match."""
        mock_er_client = MagicMock()
        mock_boto3.client.return_value = mock_er_client
        mock_er_client.get_match_id.return_value = {"matchId": ""}

        event = {
            "operation": "lookup",
            "source_system": "UNKNOWN_SYS",
            "source_id": "000000",
        }

        result = handler(event, None)

        assert result["status"] == "no_match"
        assert result["canonical_uri"] == ""

    def test_missing_source_system_rejected(self):
        """lookup without source_system returns validation error."""
        event = {
            "operation": "lookup",
            "source_id": "4711837",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "source_system" in result["message"]

    @patch("handler.boto3")
    def test_er_service_failure(self, mock_boto3):
        """When ER service throws, handler returns structured error."""
        mock_er_client = MagicMock()
        mock_boto3.client.return_value = mock_er_client
        mock_er_client.get_match_id.side_effect = Exception("Service unavailable")

        event = {
            "operation": "lookup",
            "source_system": "SAP_KNA1",
            "source_id": "4711837",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "er_lookup_error"


class TestResolveOperation:
    """Tests for the resolve operation."""

    @patch("handler.boto3")
    def test_happy_path_resolve(self, mock_boto3):
        """A valid resolve returns match_id and canonical URI."""
        mock_er_client = MagicMock()
        mock_boto3.client.return_value = mock_er_client
        mock_er_client.get_match_id.return_value = {"matchId": "abc123"}

        event = {
            "operation": "resolve",
            "record_attributes": {
                "first_name": "Anjali",
                "last_name": "Patel",
                "ssn_last4": "1234",
            },
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["match_id"] == "abc123"
        assert result["canonical_uri"] == "atlas:entity/abc123"

    def test_missing_record_attributes_rejected(self):
        """resolve without record_attributes returns validation error."""
        event = {"operation": "resolve"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert "record_attributes" in result["message"]


class TestLinkOperation:
    """Tests for the link operation."""

    def test_happy_path_link(self):
        """A valid link records the association."""
        event = {
            "operation": "link",
            "source_record_uri": "sap:kna1/4711837",
            "canonical_uri": "atlas:cust/9c2a1e",
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["link_recorded"] is True

    def test_missing_canonical_uri_rejected(self):
        """link without canonical_uri returns validation error."""
        event = {
            "operation": "link",
            "source_record_uri": "sap:kna1/4711837",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert "canonical_uri" in result["message"]


class TestInvalidOperation:
    """Tests for unknown operations."""

    def test_unknown_operation_rejected(self):
        event = {"operation": "delete_all_links"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "invalid_operation"
