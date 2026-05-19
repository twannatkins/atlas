"""
notify-advisor — Step Functions sub-Lambda #4.

Sends notification to the selected advisor. In the workshop, this emits
a CloudWatch event. In production, this integrates with the advisor's
CRM or notification system.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Notify the selected advisor of the incoming referral."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    household_uri = event.get("household_uri", "")
    routing_decision_uri = event.get("routing_decision_uri", "")

    if not selected_advisor_uri:
        return {**event, "status": "workflow_error", "error": "No advisor to notify"}

    # Emit CloudWatch event (workshop notification mechanism)
    try:
        events_client = boto3.client("events")
        events_client.put_events(
            Entries=[{
                "Source": "atlas.referral-orchestrator",
                "DetailType": "ReferralRouted",
                "Detail": json.dumps({
                    "routing_decision_uri": routing_decision_uri,
                    "selected_advisor_uri": selected_advisor_uri,
                    "household_uri": household_uri,
                    "invocation_id": invocation_id,
                }),
            }]
        )
    except Exception as exc:
        logger.warning(json.dumps({"invocation_id": invocation_id, "warning": f"Notification failed: {exc}"}))
        # Notification failure is non-fatal — the routing decision is already written
        return {**event, "status": "notification_failed", "notification_error": str(exc)}

    return {**event, "status": "advisor_notified"}
