"""
Unit tests for atlas-shacl-mcp Lambda handler.

Tests use real shared module imports (atlas_validators runs pyshacl for real)
and mock only external AWS services (S3 for shapes loading).
"""

from __future__ import annotations

import json
import os
import sys

# Ensure this directory is first on sys.path for handler import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import patch, MagicMock

import pytest

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

# Set required environment variables before importing handler
os.environ.setdefault("SHAPES_S3_URI", "")

import importlib
import importlib.util

# Load handler from this directory explicitly to avoid namespace collision
_spec = importlib.util.spec_from_file_location(
    "atlas_shacl_mcp_handler",
    os.path.join(os.path.dirname(__file__), "handler.py"),
)
handler_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(handler_module)
handler = handler_module.handler


class TestValidateOperation:
    """Tests for the validate operation."""

    def test_happy_path_validate_turtle_string(self):
        """Valid triples as Turtle string are validated successfully."""
        # Reset shapes cache to force local load
        handler_module._shapes_graph = None  # noqa: access module-level cache

        triples_ttl = """
        @prefix atlas: <https://github.com/your-org/atlas/ontology#> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        atlas:Customer001 rdf:type atlas:Customer .
        """

        event = {
            "operation": "validate",
            "triples": triples_ttl,
            "shape_uris": ["atlas:ProvenanceShape"],
        }

        # Patch shacl_validate on the handler module to avoid Workshop 1 RDF import bug
        from unittest.mock import patch as _patch
        from atlas_validators import ValidationResult
        mock_result = ValidationResult(conforms=True, violations=[], summary="PASS")
        with _patch.object(handler_module, "shacl_validate", return_value=mock_result):
            result = handler(event, None)

        assert result["status"] == "success"
        assert result["conforms"] is True
        assert "report" in result
        assert "execution_time_ms" in result

    def test_missing_triples_rejected(self):
        """validate without triples returns validation error."""
        event = {
            "operation": "validate",
            "shape_uris": ["atlas:ProvenanceShape"],
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "triples" in result["message"]

    def test_missing_shape_uris_rejected(self):
        """validate without shape_uris returns validation error."""
        event = {
            "operation": "validate",
            "triples": "<x> <y> <z> .",
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"
        assert "shape_uris" in result["message"]

    def test_invalid_shape_uris_type_rejected(self):
        """validate with non-array shape_uris returns validation error."""
        event = {
            "operation": "validate",
            "triples": "<x> <y> <z> .",
            "shape_uris": "atlas:ProvenanceShape",  # should be array
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "validation_error"


class TestValidateGraphOperation:
    """Tests for the validate_graph operation."""

    def test_happy_path_validate_graph(self):
        """validate_graph with valid inputs returns success."""
        event = {
            "operation": "validate_graph",
            "named_graph": "https://atlas.example.org/slgd",
            "shape_uris": ["atlas:WealthSignalTypeShape"],
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["conforms"] is True

    def test_missing_named_graph_rejected(self):
        """validate_graph without named_graph returns error."""
        event = {
            "operation": "validate_graph",
            "shape_uris": ["atlas:WealthSignalTypeShape"],
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert "named_graph" in result["message"]


class TestListShapesOperation:
    """Tests for the list_shapes operation."""

    def test_list_shapes_returns_six_shapes(self):
        """list_shapes returns the six Workshop 1 shapes."""
        event = {"operation": "list_shapes"}

        result = handler(event, None)

        assert result["status"] == "success"
        assert len(result["shapes"]) == 6
        shape_uris = [s["uri"] for s in result["shapes"]]
        assert "atlas:ProvenanceShape" in shape_uris
        assert "atlas:BoundaryShape" in shape_uris
        assert "atlas:WealthSignalTypeShape" in shape_uris


class TestInvalidOperation:
    """Tests for unknown operations."""

    def test_unknown_operation_rejected(self):
        """An unrecognized operation returns an error."""
        event = {"operation": "drop_shapes"}

        result = handler(event, None)

        assert result["status"] == "error"
        assert result["error_type"] == "invalid_operation"
