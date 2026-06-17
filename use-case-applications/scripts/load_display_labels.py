#!/usr/bin/env python3
"""Load human-readable rdfs:label triples onto the promoted SLGD entities.

Why this exists
---------------
WS1's entity-resolution promotion (05_entity_resolution.ipynb) writes the structural
facts for each customer/advisor/household — atlas:customerId, atlas:hasAccount,
atlas:memberOf, derived wealth signals — but NO human name. The customer-master.json /
advisors.json fixtures DO carry the synthetic names (first_name/last_name); they just
were never promoted as rdfs:label. So the UIs showed raw UUIDs.

This script closes that gap: it reads the SAME authoritative fixtures the SLGD was built
from and writes one rdfs:label per entity, keyed by the resolved URI form the promotion
used (customer-{id}-resolved, advisor-{id}-resolved, household-{id}). The labels are
real synthetic names — nothing invented — written through the governed MCP update path
(SigV4 + neptune-db:WriteDataViaQuery), exactly like every other SLGD write.

Two teaching protagonists get deliberate labels so the workshop's referral scenario reads
naturally (these are synthetic entities; the names are a teaching overlay, documented):
  - the referral-subject customer c6b6e4ad…  -> "Rachel Kim"
  - one WEALTH advisor (first in advisors.json) -> "Marcus Webb"
Everyone else keeps their fixture name. Re-running is idempotent (INSERT DATA of the same
label triple is a no-op in Neptune).

Usage
-----
    python3 load_display_labels.py            # load all labels
    python3 load_display_labels.py --dry-run  # print the triples, write nothing

Requires AWS credentials with bedrock-agentcore:InvokeAgentRuntime on the sparql MCP and
the MCP in MCP_AUTH_MODE=sigv4 (the live default). Run from anywhere with network access
to the AgentCore control plane — the MCP itself reaches Neptune from inside the VPC.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
# The sparql MCP runtime ARN. REQUIRED — pass your own deploy's ARN (the AtlasSparqlMcpArn
# stack output). There is deliberately NO default: a hardcoded fallback would carry one
# account's ARN and silently target someone else's (or a nonexistent) runtime on a fresh
# deploy. Fetch it from your stack, e.g.:
#   export SPARQL_MCP_ARN=$(aws cloudformation describe-stacks --stack-name AtlasWorkshop2 \
#     --query "Stacks[0].Outputs[?OutputKey=='AtlasSparqlMcpArn'].OutputValue" --output text)
SPARQL_MCP_ARN = os.environ.get("SPARQL_MCP_ARN", "")
INST = "https://github.com/your-org/atlas/instance#"
FIXTURES = Path(__file__).resolve().parents[2] / "agentic-semantic-layer" / "data" / "synthetic"

# Deliberate teaching labels (synthetic entities; documented overlay — see module docstring).
RACHEL_KIM_PREFIX = "c6b6e4ad"  # the referral-subject customer in the workshop scenario


def _escape(s: str) -> str:
    """Escape a string literal for SPARQL (quotes + backslashes)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_label_triples() -> list[str]:
    """Build N-Triples-ish 'rdfs:label' lines from the fixtures (resolved-URI keyed)."""
    customers = json.loads((FIXTURES / "customer-master.json").read_text())
    advisors = json.loads((FIXTURES / "advisors.json").read_text())

    triples: list[str] = []
    seen_households: set[str] = set()

    # The first WEALTH advisor becomes "Marcus Webb" (the wealth-advisor protagonist).
    wealth_advisors = [a for a in advisors if a.get("line_of_business") == "WEALTH"]
    marcus_id = wealth_advisors[0]["advisor_id"] if wealth_advisors else None

    for c in customers:
        cid = c["customer_id"]
        if cid.startswith(RACHEL_KIM_PREFIX):
            name = "Rachel Kim"
        else:
            name = f'{c["first_name"]} {c["last_name"]}'
        uri = f"{INST}customer-{cid}-resolved"
        triples.append(f'<{uri}> <http://www.w3.org/2000/01/rdf-schema#label> "{_escape(name)}" .')

        # Label the household once, with a readable household name (the primary member's
        # surname + "Household") — a real, derived label, not invented data.
        hh = c.get("household_id")
        if hh and hh not in seen_households:
            seen_households.add(hh)
            surname = "Rachel Kim" if cid.startswith(RACHEL_KIM_PREFIX) else c["last_name"]
            hh_name = f'{surname.split()[-1]} household'
            hh_uri = f"{INST}household-{hh}"
            triples.append(
                f'<{hh_uri}> <http://www.w3.org/2000/01/rdf-schema#label> "{_escape(hh_name)}" .'
            )

    for a in advisors:
        aid = a["advisor_id"]
        if aid == marcus_id:
            name = "Marcus Webb"
        else:
            name = f'{a["first_name"]} {a["last_name"]}'
        uri = f"{INST}advisor-{aid}-resolved"
        triples.append(f'<{uri}> <http://www.w3.org/2000/01/rdf-schema#label> "{_escape(name)}" .')

    return triples


def insert_via_mcp(triples: list[str], batch_size: int = 50) -> int:
    """INSERT DATA the label triples through the sparql MCP (SigV4), in batches."""
    client = boto3.client("bedrock-agentcore", region_name=REGION)
    written = 0
    for i in range(0, len(triples), batch_size):
        batch = triples[i : i + batch_size]
        # The MCP update validator requires the atlas: and prov: prefixes declared on any
        # write (its boundary check). We declare the full standard preamble; the triples
        # use full IRIs, so the body itself is unambiguous regardless.
        update = (
            "PREFIX atlas: <https://github.com/your-org/atlas/ontology#>\n"
            "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "INSERT DATA {\n" + "\n".join(batch) + "\n}"
        )
        payload = {
            "operation": "update",
            "persona_claim": "atlas-ontology-steward",
            "graph_tier": "slgd",
            "sparql": update,
        }
        resp = client.invoke_agent_runtime(
            agentRuntimeArn=SPARQL_MCP_ARN, payload=json.dumps(payload).encode()
        )
        raw = resp["response"].read()
        result = json.loads(raw)
        if result.get("status") != "success":
            print(f"  [FAIL] batch {i // batch_size}: {result}", file=sys.stderr)
            raise RuntimeError(f"MCP update failed: {result}")
        written += len(batch)
        print(f"  wrote {written}/{len(triples)} label triples")
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print triples, write nothing")
    args = ap.parse_args()

    # SPARQL_MCP_ARN is required for any write (the --dry-run path only prints triples and
    # never touches the MCP, so it is allowed to run without it).
    if not args.dry_run and not SPARQL_MCP_ARN:
        print("ERROR: SPARQL_MCP_ARN is not set.", file=sys.stderr)
        print(
            "Pass your sparql MCP runtime ARN from the stack output AtlasSparqlMcpArn, e.g.:\n"
            "  export SPARQL_MCP_ARN=$(aws cloudformation describe-stacks "
            "--stack-name AtlasWorkshop2 \\\n"
            "    --query \"Stacks[0].Outputs[?OutputKey=='AtlasSparqlMcpArn'].OutputValue\" "
            "--output text)\n"
            "  python3 load_display_labels.py\n"
            "(or run with --dry-run to print the triples without writing).",
            file=sys.stderr,
        )
        return 1

    triples = build_label_triples()
    print(f"Built {len(triples)} rdfs:label triples from the synthetic fixtures.")
    print("Sample:")
    for t in triples[:4]:
        print("  " + t)

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    written = insert_via_mcp(triples)
    print(f"\nDone. {written} rdfs:label triples written to the SLGD via the sparql MCP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
