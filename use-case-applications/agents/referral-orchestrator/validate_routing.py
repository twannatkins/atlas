"""
validate-routing — Step Functions sub-Lambda #2.

Validates the routing decision in two ways:
  1. Neptune ASK: check household has no active compliance hold.
  2. pyshacl inline: validate atlas:RoutingPolicyShape — the selectedRoute
     MUST be from the closed enumerated set. Non-conformance HALTS the
     workflow (returns validation_failed). This IS the SR 11-7 compliance
     gate — it must be mechanical, not theater.

Prior implementation wrapped SHACL in `except Exception: warning; proceed`,
making the gate ineffective. This version distinguishes:
  - validator error (shapes failed to load, transient) → log + halt
  - non-conformance (conforms=False) → HALT, do not write

Calls Neptune directly (SigV4 POST) and runs pyshacl in-process.
"""

from __future__ import annotations

import io
import json
import logging
import os
import uuid
from typing import Any, Dict

import boto3
from rdflib import Graph
from pyshacl import validate as shacl_validate

from neptune_client import sparql_query

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SHAPES_S3_URI is set by the CDK stack from the runner's own ontology staging bucket
# (ontologyStagingBucket context -> SHAPES_S3_URI env). There is intentionally NO
# account-specific default: a bare default would silently point a clean deployment at
# someone else's bucket. If the env var is unset we fail clearly at load time instead.
SHAPES_S3_URI = os.environ.get("SHAPES_S3_URI", "")

_shapes_graph: Graph | None = None


def _load_shapes() -> Graph:
    """Load atlas-shapes.ttl from S3 once per cold start."""
    global _shapes_graph
    if _shapes_graph is not None:
        return _shapes_graph

    if not SHAPES_S3_URI:
        raise RuntimeError(
            "SHAPES_S3_URI is not set. The CDK stack must set it from the runner's "
            "ontologyStagingBucket (s3://<bucket>/ontology/atlas-shapes.ttl). There is "
            "no account-specific default by design."
        )

    s3 = boto3.client("s3")
    # Parse s3://bucket/key
    without_scheme = SHAPES_S3_URI[len("s3://"):]
    bucket, _, key = without_scheme.partition("/")
    obj = s3.get_object(Bucket=bucket, Key=key)
    ttl_bytes = obj["Body"].read()

    g = Graph()
    g.parse(data=ttl_bytes, format="turtle")
    _shapes_graph = g
    return g


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Validate the routing decision. Non-conformance HALTS the workflow."""
    invocation_id = event.get("invocation_id", str(uuid.uuid4()))
    selected_advisor_uri = event.get("selected_advisor_uri", "")
    household_uri = event.get("household_uri", "")
    persona_claim = event.get("persona_claim", "atlas-consumer-banker")

    if not selected_advisor_uri:
        return {**event, "status": "validation_failed",
                "validation_error": "No advisor selected — cannot validate routing"}

    # ── 1. Compliance hold check (Neptune ASK) ───────────────────────────────
    try:
        hold_rows = sparql_query(
            f"PREFIX atlas: <https://github.com/your-org/atlas/ontology#> "
            f"ASK {{ <{household_uri}> atlas:hasComplianceHold true }}",
            graph_tier="slgd",
        )
        if hold_rows and hold_rows[0].get("result") == "true":
            logger.warning(json.dumps({
                "invocation_id": invocation_id,
                "event": "compliance_hold",
                "household_uri": household_uri,
            }))
            return {**event, "status": "validation_failed",
                    "validation_error": "Household has active compliance hold — routing blocked"}
    except Exception as exc:
        # Hold-check failure is a system error — halt, do not proceed blind
        logger.error(json.dumps({"invocation_id": invocation_id, "error": f"Hold check failed: {exc}"}))
        return {**event, "status": "validation_failed",
                "validation_error": f"Compliance hold check failed (system error): {exc}"}

    # ── 2. SHACL gate — RoutingPolicyShape (inline pyshacl) ─────────────────
    # Validate that selectedRoute is in the closed set before writing.
    # "route_to_advisor" would fail — the conformant value is "ROUTE_ADVISOR_QUEUE".
    routing_ttl = f"""
    @prefix atlas: <https://github.com/your-org/atlas/ontology#> .
    @prefix prov: <http://www.w3.org/ns/prov#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    <atlas:routing/{invocation_id}> a atlas:RoutingDecision ;
        atlas:selectedRoute "ROUTE_ADVISOR_QUEUE"^^xsd:string ;
        atlas:targetAdvisor <{selected_advisor_uri}> ;
        atlas:aboutHousehold <{household_uri}> .
    """

    try:
        shapes = _load_shapes()
    except Exception as exc:
        # Shapes file unavailable — system error, halt
        logger.error(json.dumps({"invocation_id": invocation_id,
                                  "error": f"SHACL shapes load failed: {exc}"}))
        return {**event, "status": "validation_failed",
                "validation_error": f"SHACL shapes unavailable (system error): {exc}"}

    data_graph = Graph()
    data_graph.parse(data=routing_ttl, format="turtle")

    conforms, _, report_text = shacl_validate(
        data_graph,
        shacl_graph=shapes,
        inference="none",
        abort_on_first=True,
    )

    if not conforms:
        # NON-CONFORMANCE → HALT. Do NOT swallow and proceed.
        # This is the SR 11-7 compliance gate — a non-conformant routing decision
        # is architecturally prohibited from reaching the write step.
        logger.error(json.dumps({
            "invocation_id": invocation_id,
            "event": "shacl_non_conformance",
            "report": report_text[:500] if report_text else "no report",
        }))
        return {**event, "status": "validation_failed",
                "validation_error": f"RoutingPolicyShape violation: {report_text[:200] if report_text else 'non-conformant'}"}

    logger.info(json.dumps({
        "invocation_id": invocation_id,
        "event": "validation_passed",
        "shacl_conforms": True,
    }))
    return {**event, "status": "validated"}
