"""
Shared Neptune SigV4 client for referral-orchestrator step Lambdas.
Uses urllib (stdlib) — no extra dependencies.
POST-based SigV4 signing avoids query-string canonicalization failures
against Neptune IAM auth with prefixed SPARQL queries.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
NEPTUNE_SLGD_ENDPOINT = os.environ.get("NEPTUNE_SLGD_ENDPOINT", "")
NEPTUNE_LGD_ENDPOINT = os.environ.get("NEPTUNE_LGD_ENDPOINT", "")

_boto_session = boto3.Session()


def _sigv4_headers(method: str, url: str, headers: Dict[str, str], body: str = "") -> Dict[str, str]:
    credentials = _boto_session.get_credentials().get_frozen_credentials()
    req = AWSRequest(method=method, url=url, headers=headers, data=body)
    SigV4Auth(credentials, "neptune-db", AWS_REGION).add_auth(req)
    return dict(req.headers)


def sparql_query(sparql: str, graph_tier: str = "slgd") -> List[Dict[str, Any]]:
    """Execute a SELECT/ASK query against Neptune via SigV4-signed POST (urllib)."""
    endpoint = NEPTUNE_SLGD_ENDPOINT if graph_tier == "slgd" else NEPTUNE_LGD_ENDPOINT
    url = f"https://{endpoint}:8182/sparql"
    body = f"query={urllib.parse.quote(sparql)}"
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    signed = _sigv4_headers("POST", url, headers, body)
    req = urllib.request.Request(url, data=body.encode(), method="POST")
    for k, v in signed.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if "results" in result and "bindings" in result["results"]:
        vars_ = result.get("head", {}).get("vars", [])
        return [
            {v: b[v]["value"] for v in vars_ if v in b}
            for b in result["results"]["bindings"]
        ]
    if "boolean" in result:
        return [{"result": str(result["boolean"]).lower()}]
    return []


def sparql_update(sparql: str) -> None:
    """Execute a SPARQL UPDATE against the SLGD via SigV4-signed POST (urllib)."""
    url = f"https://{NEPTUNE_SLGD_ENDPOINT}:8182/sparql"
    body = f"update={urllib.parse.quote(sparql)}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    signed = _sigv4_headers("POST", url, headers, body)
    req = urllib.request.Request(url, data=body.encode(), method="POST")
    for k, v in signed.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()
