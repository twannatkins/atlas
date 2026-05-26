"""
conversational-context-manager — Maintains multi-turn conversation context
for the Wealth UI's conversational surface using AgentCore Memory.

Memory is session-scoped: persists across turns within a session, clears
at session end. Wraps nl-to-sparql-agent with session-aware context so
follow-up questions like "of those, which..." work correctly.

Component class: MEMORY-BACKED, SESSION-SCOPED.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

NL_TO_SPARQL_AGENT_ARN = os.environ.get("NL_TO_SPARQL_AGENT_ARN", "")
AGENTCORE_MEMORY_NAMESPACE = os.environ.get("AGENTCORE_MEMORY_NAMESPACE", "atlas-wealth-conv")

VALID_PERSONAS = ["atlas-wealth-advisor"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for conversational-context-manager."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        question = event.get("question")
        session_id = event.get("session_id")
        persona_claim = event.get("persona_claim")

        if not question or not isinstance(question, str):
            return _error_response(invocation_id, start_time, "validation_error",
                                   "question is required")
        if not session_id or not isinstance(session_id, str):
            return _error_response(invocation_id, start_time, "validation_error",
                                   "session_id is required")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "validation_error",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Step 1: Load prior context from AgentCore Memory
        prior_context = _load_session_context(session_id)

        # Step 2: Invoke nl-to-sparql-agent with question + context
        try:
            nl_result = _invoke_nl_to_sparql(question, persona_claim, session_id, prior_context)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "query_error",
                                   f"nl-to-sparql-agent invocation failed: {exc}")

        # Step 3: Persist new turn to AgentCore Memory
        _save_session_context(session_id, question, nl_result)

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "converse")

        return {
            "status": nl_result.get("status", "success"),
            "sparql": nl_result.get("sparql", ""),
            "result": nl_result.get("result", []),
            "context_used": {
                "session_id": session_id,
                "prior_turns": len(prior_context.get("turns", [])),
            },
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return _error_response(invocation_id, start_time, "query_error", str(exc))


def _load_session_context(session_id: str) -> dict:
    """Load session context from AgentCore Memory."""
    try:
        memory_client = boto3.client("bedrock-agentcore")
        response = memory_client.get_memory(
            memoryId=f"{AGENTCORE_MEMORY_NAMESPACE}/{session_id}",
        )
        content = response.get("content", "{}")
        return json.loads(content) if isinstance(content, str) else content
    except Exception:
        # No prior context — first turn in session
        return {"turns": []}


def _save_session_context(session_id: str, question: str, result: dict) -> None:
    """Save the current turn to AgentCore Memory."""
    try:
        # Load existing context
        context = _load_session_context(session_id)
        turns = context.get("turns", [])

        # Append new turn (keep last 10 turns to bound memory)
        turns.append({
            "question": question,
            "sparql": result.get("sparql", ""),
            "result_count": len(result.get("result", [])),
        })
        turns = turns[-10:]

        memory_client = boto3.client("bedrock-agentcore")
        memory_client.put_memory(
            memoryId=f"{AGENTCORE_MEMORY_NAMESPACE}/{session_id}",
            content=json.dumps({"turns": turns}),
        )
    except Exception as exc:
        # Memory save failure is non-fatal — the query still succeeded
        logger.warning(json.dumps({"warning": f"Failed to save session context: {exc}"}))


def _invoke_nl_to_sparql(question: str, persona_claim: str, session_id: str, prior_context: dict) -> dict:
    """Invoke nl-to-sparql-agent with optional session context."""
    lambda_client = boto3.client("lambda")

    payload = {
        "question": question,
        "persona_claim": persona_claim,
        "session_id": session_id,
    }

    # If there's prior context, augment the question with it
    if prior_context.get("turns"):
        last_turn = prior_context["turns"][-1]
        payload["prior_sparql"] = last_turn.get("sparql", "")

    response = lambda_client.invoke(
        FunctionName=NL_TO_SPARQL_AGENT_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    result = json.loads(response["Payload"].read())
    return result


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "sparql": "",
        "result": [],
        "context_used": {},
        "error_message": message,
        "invocation_id": invocation_id,
        "execution_time_ms": execution_time_ms,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "conversational-context-manager",
    }))
