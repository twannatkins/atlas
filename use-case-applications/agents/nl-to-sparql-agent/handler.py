"""
nl-to-sparql-agent — Translates natural-language questions into SPARQL
queries against the Neptune SLGD using validated query templates.

Foundational agent; deterministic by construction. Uses Bedrock Titan
embeddings for semantic similarity matching against templates in
ground-truth.yaml. Does NOT call any text-generation model. Free SPARQL
generation is forbidden.

Component class: DETERMINISTIC-AUDITED — same question = same SPARQL.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Add shared modules to path for Workshop 1 helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "agentic-semantic-layer", "notebooks", "shared"))

from atlas_sparql import validate, AtlasSPARQLError, prefixed

import boto3
import yaml

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment
GROUND_TRUTH_S3_URI = os.environ.get("GROUND_TRUTH_S3_URI", "")
PREFIXES_S3_URI = os.environ.get("PREFIXES_S3_URI", "")
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
BEDROCK_EMBEDDING_MODEL_ID = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

VALID_PERSONAS = [
    "atlas-consumer-banker",
    "atlas-wealth-advisor",
    "atlas-bsa-analyst",
    "atlas-ontology-steward",
    "atlas-auditor",
]

# Cached templates (loaded once per cold start)
_templates: List[Dict[str, Any]] | None = None
_prefix_preamble: str | None = None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for nl-to-sparql-agent."""
    invocation_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Input validation
        question = event.get("question")
        persona_claim = event.get("persona_claim")

        if not question or not isinstance(question, str):
            return _error_response(invocation_id, start_time, "no_template_match",
                                   "question is required and must be a string")
        if len(question) > 500:
            return _error_response(invocation_id, start_time, "no_template_match",
                                   "question must be 500 characters or fewer")
        if not persona_claim or persona_claim not in VALID_PERSONAS:
            return _error_response(invocation_id, start_time, "no_template_match",
                                   f"persona_claim must be one of: {VALID_PERSONAS}")

        # Load templates and prefixes
        templates = _load_templates()
        prefix_preamble = _load_prefixes()

        # Step 1: Generate embedding for the question
        question_embedding = _get_embedding(question)

        # Step 2: Match against template questions
        best_match = _find_best_template(question_embedding, templates)

        if best_match is None:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _emit_log(invocation_id, persona_claim, execution_time_ms, "no_template_match", "query")
            return {
                "status": "no_template_match",
                "sparql": "",
                "result": [],
                "provenance": {
                    "template_id": "",
                    "parameters": {},
                    "execution_time_ms": execution_time_ms,
                },
                "invocation_id": invocation_id,
            }

        template = best_match["template"]
        template_id = best_match["template_id"]
        parameters = best_match.get("parameters", {})

        # Step 3: Build SPARQL from template
        sparql_query = template["sparql"].strip()

        # Step 4: Validate SPARQL
        try:
            validate(sparql_query)
        except AtlasSPARQLError as exc:
            return _error_response(invocation_id, start_time, "parameter_extraction_failed",
                                   f"Generated SPARQL failed validation: {exc}")

        # Step 5: Execute via atlas-sparql-mcp
        try:
            result_rows = _invoke_sparql_mcp(sparql_query, persona_claim)
        except Exception as exc:
            execution_time_ms = int((time.time() - start_time) * 1000)
            _emit_log(invocation_id, persona_claim, execution_time_ms, "execution_error", "query")
            return {
                "status": "execution_error",
                "sparql": sparql_query,
                "result": [],
                "provenance": {
                    "template_id": template_id,
                    "parameters": parameters,
                    "execution_time_ms": execution_time_ms,
                },
                "error_message": str(exc),
                "invocation_id": invocation_id,
            }

        execution_time_ms = int((time.time() - start_time) * 1000)
        _emit_log(invocation_id, persona_claim, execution_time_ms, "success", "query")

        return {
            "status": "success",
            "sparql": sparql_query,
            "result": result_rows,
            "provenance": {
                "template_id": template_id,
                "parameters": parameters,
                "execution_time_ms": execution_time_ms,
            },
            "invocation_id": invocation_id,
        }

    except Exception as exc:
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }))
        return _error_response(invocation_id, start_time, "execution_error", str(exc))


def _get_embedding(text: str) -> List[float]:
    """Generate embedding via Bedrock Titan Embed v2."""
    bedrock = boto3.client("bedrock-runtime")
    response = bedrock.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": text}),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def _find_best_template(question_embedding: List[float], templates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the best-matching template using cosine similarity.

    Returns None if no template exceeds the similarity threshold.
    """
    SIMILARITY_THRESHOLD = 0.75
    best_score = -1.0
    best_match = None

    for i, template in enumerate(templates):
        # Generate embedding for template question (in production, these would be pre-computed)
        template_embedding = _get_embedding(template["question"])
        score = _cosine_similarity(question_embedding, template_embedding)

        if score > best_score:
            best_score = score
            best_match = {
                "template": template,
                "template_id": template.get("note", f"template-{i}"),
                "parameters": {},
                "similarity_score": score,
            }

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        return best_match
    return None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _invoke_sparql_mcp(sparql: str, persona_claim: str) -> list:
    """Invoke atlas-sparql-mcp for query execution."""
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
        raise RuntimeError(result.get("message", "SPARQL MCP returned error"))
    return result.get("rows", [])


def _load_templates() -> List[Dict[str, Any]]:
    """Load ground-truth templates from S3 or local fallback."""
    global _templates
    if _templates is not None:
        return _templates

    if GROUND_TRUTH_S3_URI:
        parts = GROUND_TRUTH_S3_URI.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        data = yaml.safe_load(content)
    else:
        # Local fallback for development/testing
        local_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "agentic-semantic-layer", "prompts", "ground-truth.yaml"
        )
        with open(local_path, "r") as f:
            data = yaml.safe_load(f)

    _templates = data.get("pairs", [])
    return _templates


def _load_prefixes() -> str:
    """Load SPARQL prefix preamble from S3 or local fallback."""
    global _prefix_preamble
    if _prefix_preamble is not None:
        return _prefix_preamble

    if PREFIXES_S3_URI:
        parts = PREFIXES_S3_URI.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        _prefix_preamble = response["Body"].read().decode("utf-8")
    else:
        local_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "agentic-semantic-layer", "prompts", "prefixes.txt"
        )
        if os.path.exists(local_path):
            with open(local_path, "r") as f:
                _prefix_preamble = f.read()
        else:
            _prefix_preamble = ""

    return _prefix_preamble


def _error_response(invocation_id: str, start_time: float, status: str, message: str) -> Dict[str, Any]:
    """Build a structured error response conforming to output_schema."""
    execution_time_ms = int((time.time() - start_time) * 1000)
    _emit_log(invocation_id, "unknown", execution_time_ms, status, "error")
    return {
        "status": status,
        "sparql": "",
        "result": [],
        "provenance": {
            "template_id": "",
            "parameters": {},
            "execution_time_ms": execution_time_ms,
        },
        "clarification_request": message if status == "parameter_extraction_failed" else "",
        "invocation_id": invocation_id,
    }


def _emit_log(invocation_id: str, persona_claim: str, execution_time_ms: int, status: str, operation: str) -> None:
    """Emit structured JSON audit log."""
    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "persona_claim": persona_claim,
        "execution_time_ms": execution_time_ms,
        "status": status,
        "operation": operation,
        "agent": "nl-to-sparql-agent",
    }))
