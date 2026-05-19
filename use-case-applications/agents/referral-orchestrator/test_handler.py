"""
Unit tests for referral-orchestrator Lambda handler and sub-Lambdas.

Tests the orchestrator entry point and each of the 5 sub-Lambdas.
Mocks Step Functions and Lambda invocations.
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

os.environ.setdefault("STATE_MACHINE_ARN", "arn:aws:states:us-east-1:123456789012:stateMachine:referral-orchestrator")
os.environ.setdefault("SPARQL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-sparql-mcp")
os.environ.setdefault("SHACL_MCP_ARN", "arn:aws:lambda:us-east-1:123456789012:function:atlas-shacl-mcp")

from handler import handler
from select_advisor import handler as select_advisor_handler
from validate_routing import handler as validate_routing_handler
from write_routing_decision import handler as write_routing_decision_handler
from notify_advisor import handler as notify_advisor_handler
from audit_write import handler as audit_write_handler


class TestOrchestratorEntryPoint:
    """Tests for the main orchestrator handler."""

    @patch("handler.boto3")
    def test_happy_path_starts_execution(self, mock_boto3):
        """Valid input starts a Step Functions execution."""
        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn
        mock_sfn.start_execution.return_value = {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:referral-orchestrator:referral-abc"
        }

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "approved_rationale": "Strong wealth signals detected.",
            "originating_banker_id": "banker-rachel-kim",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "routed"
        assert result["execution_arn"] != ""
        assert result["routing_decision_uri"] != ""
        assert result["audit_record_uri"] != ""

    def test_missing_approved_rationale_rejected(self):
        """Handler rejects event without approved_rationale (human must approve first)."""
        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "originating_banker_id": "banker-rachel-kim",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "workflow_error"
        assert "approved_rationale" in result.get("error_message", "")

    def test_non_consumer_banker_rejected(self):
        """Only atlas-consumer-banker can invoke the orchestrator."""
        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "approved_rationale": "Approved.",
            "originating_banker_id": "banker-001",
            "persona_claim": "atlas-wealth-advisor",
        }

        result = handler(event, None)

        assert result["status"] == "workflow_error"

    @patch("handler.boto3")
    def test_step_functions_failure(self, mock_boto3):
        """When Step Functions fails to start, handler returns workflow_error."""
        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn
        mock_sfn.start_execution.side_effect = Exception("State machine not found")

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "signal_uris": ["atlas:signal/001"],
            "approved_rationale": "Approved.",
            "originating_banker_id": "banker-001",
            "persona_claim": "atlas-consumer-banker",
        }

        result = handler(event, None)

        assert result["status"] == "workflow_error"


class TestSelectAdvisor:
    """Tests for the select-advisor sub-Lambda."""

    @patch("select_advisor.boto3")
    def test_selects_top_advisor(self, mock_boto3):
        """Returns the top-ranked advisor from SPARQL results."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        sparql_result = json.dumps({
            "status": "success",
            "rows": [
                {"advisor": "atlas:advisor/001", "label": "Sarah Chen", "capacity": "5", "specialization": "wealth"},
                {"advisor": "atlas:advisor/002", "label": "James Park", "capacity": "3", "specialization": "wealth"},
            ],
        }).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=sparql_result))}

        event = {"household_uri": "atlas:hh/9c2a1e", "persona_claim": "atlas-consumer-banker"}
        result = select_advisor_handler(event, None)

        assert result["status"] == "advisor_selected"
        assert result["selected_advisor_uri"] == "atlas:advisor/001"

    @patch("select_advisor.boto3")
    def test_no_advisors_available(self, mock_boto3):
        """When no advisors are available, returns no_eligible_advisor."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        sparql_result = json.dumps({"status": "success", "rows": []}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=sparql_result))}

        event = {"household_uri": "atlas:hh/9c2a1e", "persona_claim": "atlas-consumer-banker"}
        result = select_advisor_handler(event, None)

        assert result["status"] == "no_eligible_advisor"


class TestValidateRouting:
    """Tests for the validate-routing sub-Lambda."""

    @patch("validate_routing.boto3")
    def test_valid_routing_passes(self, mock_boto3):
        """A valid routing passes SHACL validation."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        # Hold check returns no hold
        sparql_result = json.dumps({"status": "success", "rows": []}).encode()
        # SHACL validation passes
        shacl_result = json.dumps({"conforms": True, "report": {}}).encode()

        mock_lambda.invoke.side_effect = [
            {"Payload": MagicMock(read=MagicMock(return_value=sparql_result))},
            {"Payload": MagicMock(read=MagicMock(return_value=shacl_result))},
        ]

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "selected_advisor_uri": "atlas:advisor/001",
            "persona_claim": "atlas-consumer-banker",
        }
        result = validate_routing_handler(event, None)

        assert result["status"] == "validated"

    def test_no_advisor_selected_fails(self):
        """Validation fails if no advisor was selected."""
        event = {"household_uri": "atlas:hh/9c2a1e", "selected_advisor_uri": ""}
        result = validate_routing_handler(event, None)

        assert result["status"] == "validation_failed"


class TestNotifyAdvisor:
    """Tests for the notify-advisor sub-Lambda."""

    @patch("notify_advisor.boto3")
    def test_notification_sent(self, mock_boto3):
        """Notification event is emitted successfully."""
        mock_events = MagicMock()
        mock_boto3.client.return_value = mock_events

        event = {
            "selected_advisor_uri": "atlas:advisor/001",
            "household_uri": "atlas:hh/9c2a1e",
            "routing_decision_uri": "atlas:routing/abc",
        }
        result = notify_advisor_handler(event, None)

        assert result["status"] == "advisor_notified"
        mock_events.put_events.assert_called_once()

    @patch("notify_advisor.boto3")
    def test_notification_failure_non_fatal(self, mock_boto3):
        """Notification failure is non-fatal — routing decision is already written."""
        mock_events = MagicMock()
        mock_boto3.client.return_value = mock_events
        mock_events.put_events.side_effect = Exception("EventBridge unavailable")

        event = {
            "selected_advisor_uri": "atlas:advisor/001",
            "household_uri": "atlas:hh/9c2a1e",
            "routing_decision_uri": "atlas:routing/abc",
        }
        result = notify_advisor_handler(event, None)

        assert result["status"] == "notification_failed"


class TestAuditWrite:
    """Tests for the audit-write sub-Lambda."""

    @patch("audit_write.boto3")
    def test_audit_record_written(self, mock_boto3):
        """Audit record is written to SLGD."""
        mock_lambda = MagicMock()
        mock_boto3.client.return_value = mock_lambda

        sparql_result = json.dumps({"status": "success"}).encode()
        mock_lambda.invoke.return_value = {"Payload": MagicMock(read=MagicMock(return_value=sparql_result))}

        event = {
            "household_uri": "atlas:hh/9c2a1e",
            "selected_advisor_uri": "atlas:advisor/001",
            "originating_banker_id": "banker-001",
            "routing_decision_uri": "atlas:routing/abc",
            "signal_uris": ["atlas:signal/001"],
            "persona_claim": "atlas-consumer-banker",
        }
        result = audit_write_handler(event, None)

        assert result["status"] == "routed"
        assert result["audit_record_uri"] != ""
