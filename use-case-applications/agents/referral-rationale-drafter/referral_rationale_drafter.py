"""
referral-rationale-drafter — Drafts narrative rationale for a referral.

PROBABILISTIC, HUMAN-IN-THE-LOOP. Output is always a draft. The agent
never auto-files, auto-sends, or auto-decides. The human is the final
approver. Output always carries is_probabilistic=True and
requires_human_review=True — these flags are hardcoded and not configurable.

Uses Bedrock Claude for text generation. This is the first probabilistic
agent in Workshop 2 and the most regulatorily sensitive.

Component class: PROBABILISTIC — output may vary across invocations.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Dict

from atlas_sparql import validate, AtlasSPARQLError, prefixed

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
BEDROCK_TEXT_MODEL_ID = os.environ.get("BEDROCK_TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
PROMPT_TEMPLATE_S3_URI = os.environ.get("PROMPT_TEMPLATE_S3_URI", "")

VALID_PERSONAS = ["atlas-consumer-banker"]

# Cached prompt template
_prompt_template: str | None = None

DEFAULT_PROMPT_TEMPLATE = """You are drafting a referral rationale for a Consumer Banker to send to a Wealth Advisor.

Context:
- Household: {household_uri}
- Signals detected: {signals_summary}
- Household composition: {household_context}

Write a 2-3 paragraph narrative that:
1. Summarizes why this household is being referred (based on the signals)
2. Highlights relevant context the advisor should know for the first conversation
3. Does NOT recommend specific products or make compliance determinations

Keep the tone professional and factual. This is a draft that will be reviewed and edited by the banker before sending."""


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for referral-rationale-drafter."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Input validation
        household_uri = event.get("household_uri")
        signal_uris = event.get("signal_uris")
        persona_claim = event.get("persona_claim")

        if not household_uri or not isinstance(household_uri, str):
            return _error_response(invocation_id, start_time, "context_query_failed",
                                   "household_uri is required")
        # signal_uris must be a LIST, but an EMPTY list is ALLOWED: a banker can ask for a
        # draft on a household with no derived signals (or before the UI's signal query has
        # resolved). In that case we draft from the household CONTEXT alone (real members),
        # not from signals. Previously `if not signal_uris` treated [] as missing (Python:
        # `not [] == True`) and hard-rejected with context_query_failed — failing
        # Generate-Draft for those households. Default None→[] and only reject a non-list.
        if signal_uris is None:
            signal_uris = []
        if not isinstance(signal_uris, list):
            return _error_response(invocation_id, start_time, "context_query_failed",
                                   "signal_uris must be an array")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "context_query_failed",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Step 1: Query SLGD for household context
        try:
            household_context = _get_household_context(household_uri, persona_claim)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "context_query_failed",
                                   f"Failed to query household context: {exc}")

        # Step 2: Query SLGD for signal details (returns "No signals provided." for []).
        try:
            signals_summary = _get_signals_summary(signal_uris, persona_claim)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "context_query_failed",
                                   f"Failed to query signal details: {exc}")

        # HONESTY GUARD: if there are NEITHER signals NOR real household context, there is
        # nothing real to ground a rationale on — decline honestly rather than let the model
        # invent one. (Derive-don't-fabricate: a grounded draft when context exists; an
        # explicit insufficient-context status when it does not.)
        no_signals = len(signal_uris) == 0
        no_household = household_context.strip() == "No household context available."
        if no_signals and no_household:
            return _error_response(invocation_id, start_time, "insufficient_context",
                                   "No signals and no household context to ground a rationale.")

        # Step 3: Load prompt template and generate narrative
        template = _load_prompt_template()
        prompt = template.format(
            household_uri=household_uri,
            signals_summary=signals_summary,
            household_context=household_context,
        )

        try:
            draft_narrative = _invoke_bedrock(prompt)
        except Exception as exc:
            return _error_response(invocation_id, start_time, "generation_failed",
                                   f"Bedrock generation failed: {exc}")

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "draft")

        # Output always carries probabilistic flags — hardcoded, not configurable
        return {
            "status": "success",
            "draft_narrative": draft_narrative,
            "is_probabilistic": True,
            "requires_human_review": True,
            "provenance": {
                "signals_referenced": signal_uris,
                "context_queries": [household_uri],
                "prompt_template_version": "1.0.0",
                "model_id": BEDROCK_TEXT_MODEL_ID,
            },
            "invocation_id": invocation_id,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "generation_failed", str(exc))


def _get_household_context(household_uri: str, persona_claim: str) -> str:
    """Query SLGD for household composition and relevant context."""
    # prefixed() prepends the standard ATLAS PREFIX block — the atlas-sparql-mcp REJECTS
    # any query missing the required PREFIX declarations (it does not auto-add them), so a
    # raw query returned an error and left the draft ungrounded.
    sparql = prefixed(f"""
    SELECT ?member ?memberType ?label WHERE {{
        <{household_uri}> ?rel ?member .
        ?member a ?memberType .
        OPTIONAL {{ ?member rdfs:label ?label }}
    }}
    """)
    rows = _invoke_sparql_mcp(sparql, persona_claim)
    if not rows:
        return "No household context available."

    members = [f"{r.get('label', r.get('member', 'Unknown'))} ({r.get('memberType', 'Unknown')})" for r in rows]
    return f"Household members: {', '.join(members)}"


def _get_signals_summary(signal_uris: list, persona_claim: str) -> str:
    """Query SLGD for signal details."""
    if not signal_uris:
        return "No signals provided."

    summaries = []
    for uri in signal_uris[:5]:  # Cap at 5 to avoid prompt bloat
        # signalStrength does NOT exist in the synthetic data (same reason the signal card
        # omits the strength badge), so requiring it returned zero rows and left the draft
        # ungrounded. Make it OPTIONAL and join the SKOS prefLabel for a human-readable
        # signal type (WS1 types are loaded), falling back to the type URI.
        sparql = prefixed(f"""
        SELECT ?signalType ?signalLabel ?strength ?signalDate WHERE {{
            <{uri}> a atlas:WealthSignal ;
                atlas:hasSignalType ?signalType .
            OPTIONAL {{ ?signalType skos:prefLabel ?signalLabel }}
            OPTIONAL {{ <{uri}> atlas:signalStrength ?strength }}
            OPTIONAL {{ <{uri}> atlas:signalDate ?signalDate }}
        }}
        """)
        try:
            rows = _invoke_sparql_mcp(sparql, persona_claim)
            if rows:
                r = rows[0]
                label = r.get("signalLabel") or r.get("signalType", "Unknown")
                extra = []
                if r.get("strength"):
                    extra.append(f"strength: {r['strength']}")
                if r.get("signalDate"):
                    extra.append(f"observed: {r['signalDate']}")
                summaries.append(f"{label} ({', '.join(extra)})" if extra else label)
            else:
                summaries.append(f"{uri} (details unavailable)")
        except Exception:
            summaries.append(f"{uri} (query failed)")

    return "; ".join(summaries)


def _invoke_bedrock(prompt: str) -> str:
    """Invoke Bedrock Claude for text generation."""
    bedrock = boto3.client("bedrock-runtime")
    response = bedrock.invoke_model(
        modelId=BEDROCK_TEXT_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    result = json.loads(response["body"].read())
    # Extract text from Claude response format
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", "")
    return ""


def _invoke_sparql_mcp(sparql: str, persona_claim: str) -> list:
    """Invoke atlas-sparql-mcp for a read query."""
    agentcore_client = boto3.client("bedrock-agentcore")
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=SPARQL_MCP_ARN,
        payload=json.dumps({
            "operation": "query",
            "sparql": sparql,
            "persona_claim": persona_claim,
            "graph_tier": "slgd",
        }).encode(),
        contentType="application/json",
    )
    result = json.loads(response["response"].read())
    if result.get("status") == "error":
        raise RuntimeError(result.get("message", "SPARQL MCP returned error"))
    return result.get("rows", [])


def _load_prompt_template() -> str:
    """Load prompt template from S3 or use default."""
    global _prompt_template
    if _prompt_template is not None:
        return _prompt_template

    if PROMPT_TEMPLATE_S3_URI:
        try:
            parts = PROMPT_TEMPLATE_S3_URI.replace("s3://", "").split("/", 1)
            bucket, key = parts[0], parts[1]
            s3 = boto3.client("s3")
            response = s3.get_object(Bucket=bucket, Key=key)
            _prompt_template = response["Body"].read().decode("utf-8")
        except Exception:
            _prompt_template = DEFAULT_PROMPT_TEMPLATE
    else:
        _prompt_template = DEFAULT_PROMPT_TEMPLATE

    return _prompt_template


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    """Build a structured error response conforming to output_schema."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "draft_narrative": "",
        "is_probabilistic": True,
        "requires_human_review": True,
        "provenance": {
            "signals_referenced": [],
            "context_queries": [],
            "prompt_template_version": "1.0.0",
            "model_id": BEDROCK_TEXT_MODEL_ID,
        },
        "error_message": message,
        "invocation_id": invocation_id,
        "execution_time_ms": execution_time_ms,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "referral-rationale-drafter",
    }))
