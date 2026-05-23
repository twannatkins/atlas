"""
theme-summarizer — Summarizes market and portfolio themes from source
articles for the Wealth UI Themes route.

PROBABILISTIC, DRAFT-ONLY. Output is informational, not action-driving.
The agent has no path to commit anything to the graph or trigger downstream
workflows. Always carries is_probabilistic=True and requires_human_review=True.

Component class: PROBABILISTIC — output may vary across invocations.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
BEDROCK_TEXT_MODEL_ID = os.environ.get("BEDROCK_TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

VALID_PERSONAS = ["atlas-wealth-advisor"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for theme-summarizer."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        theme_uri = event.get("theme_uri")
        persona_claim = event.get("persona_claim")

        if not theme_uri or not isinstance(theme_uri, str):
            return _error_response(invocation_id, start_time, "query_failed",
                                   "theme_uri is required")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "query_failed",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Step 1: Retrieve source articles linked to the theme
        try:
            articles = _get_theme_articles(theme_uri, persona_claim)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "query_failed",
                                   f"Failed to retrieve theme articles: {exc}")

        if not articles:
            return _error_response(invocation_id, start_time, "query_failed",
                                   "No source articles found for this theme")

        # Step 2: Generate summary via Bedrock
        try:
            summary = _generate_summary(theme_uri, articles)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "generation_failed",
                                   f"Bedrock generation failed: {exc}")

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "summarize")

        return {
            "status": "success",
            "summary": summary,
            "is_probabilistic": True,
            "requires_human_review": True,
            "source_articles": [a.get("article_uri", "") for a in articles],
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({"invocation_id": invocation_id, "error": str(exc)}))
        return _error_response(invocation_id, start_time, "generation_failed", str(exc))


def _get_theme_articles(theme_uri: str, persona_claim: str) -> list:
    """Query SLGD for articles linked to the theme."""
    sparql = f"""
    SELECT ?article ?title ?source WHERE {{
        <{theme_uri}> a atlas-part-2:ThemeAssertion ;
            atlas-part-2:hasSourceArticle ?article .
        ?article rdfs:label ?title .
        OPTIONAL {{ ?article atlas-part-2:source ?source }}
    }}
    """
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=SPARQL_MCP_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "operation": "query",
            "sparql": sparql,
            "persona_claim": persona_claim,
            "graph_tier": "slgd",
        }),
    )
    result = json.loads(response["Payload"].read())
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "SPARQL query failed"))
    return result.get("rows", [])


def _generate_summary(theme_uri: str, articles: list) -> str:
    """Generate a 2-3 sentence summary via Bedrock."""
    article_titles = [a.get("title", "Untitled") for a in articles[:5]]
    prompt = f"""Summarize the following market theme in 2-3 sentences for a Wealth Advisor's morning briefing.

Theme: {theme_uri}
Source articles: {', '.join(article_titles)}

Write a concise, factual summary. Do not recommend trades or specific actions."""

    bedrock = boto3.client("bedrock-runtime")
    response = bedrock.invoke_model(
        modelId=BEDROCK_TEXT_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    result = json.loads(response["body"].read())
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "summary": "",
        "is_probabilistic": True,
        "requires_human_review": True,
        "source_articles": [],
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
        "agent": "theme-summarizer",
    }))
