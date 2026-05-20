"""
Pattern C: Real-Time Event Stream Consumer — Lambda Handler

This Lambda function consumes wealth-eligibility events from an Amazon Kinesis
Data Stream (or Amazon MSK topic) and writes them as RDF triples to the LGD
(Lexical Graph Database) via Neptune's SPARQL UPDATE endpoint.

Architecture class: DETERMINISTIC at the mapping layer. The mapping from event
JSON to RDF triples is a fixed, reproducible transformation. The event content
may originate from probabilistic sources (e.g., a transaction-monitoring model),
but the mapping itself is deterministic.

What this function does:
1. Receives a batch of events from Kinesis/MSK
2. For each event, constructs RDF triples using the atlas: ontology vocabulary
3. Writes the triples to the LGD via SPARQL INSERT DATA
4. Returns success/failure counts for the batch

What this function does NOT do:
- It does not write to the SLGD (that requires the promotion path in Module 5)
- It does not validate against SHACL shapes (that happens during promotion)
- It does not make routing decisions (that is Module 8's bounded agent)

Environment variables:
  NEPTUNE_LGD_ENDPOINT: Neptune LGD cluster endpoint
  NEPTUNE_LGD_PORT: Neptune port (default 8182)

Module: 4, Pattern C
"""

import json
import os
import base64
import urllib.request
import urllib.parse
import ssl
from datetime import datetime

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


# Neptune LGD connection details from environment
LGD_ENDPOINT = os.environ.get("NEPTUNE_LGD_ENDPOINT", "")
LGD_PORT = os.environ.get("NEPTUNE_LGD_PORT", "8182")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# ATLAS ontology namespace
ATLAS_NS = "https://github.com/your-org/atlas/ontology#"
INSTANCE_NS = "https://github.com/your-org/atlas/instance#"

# SigV4 session — reused across invocations
_boto_session = boto3.Session()


def event_to_triples(event: dict) -> str:
    """Convert a single wealth-eligibility event to N-Triples format.

    Parameters
    ----------
    event : dict
        A wealth-eligibility event with keys: event_id, event_type,
        customer_id, signal_type, amount_usd, event_timestamp, source.

    Returns
    -------
    str
        N-Triples representation of the event, ready for SPARQL INSERT DATA.
    """
    event_uri = f"<{INSTANCE_NS}event-{event['event_id']}>"
    triples = []

    # Type the event as a BehavioralEvent (raw, unvalidated — lives in LGD only)
    triples.append(
        f'{event_uri} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        f'<{ATLAS_NS}BehavioralEvent> .'
    )

    # Signal type
    if event.get("signal_type"):
        triples.append(
            f'{event_uri} <{ATLAS_NS}hasSignalType> '
            f'<{ATLAS_NS}{_signal_type_to_iri(event["signal_type"])}> .'
        )

    # Amount
    if event.get("amount_usd"):
        triples.append(
            f'{event_uri} <{ATLAS_NS}amountUSD> '
            f'"{event["amount_usd"]}"^^<http://www.w3.org/2001/XMLSchema#decimal> .'
        )

    # Timestamp
    if event.get("event_timestamp"):
        triples.append(
            f'{event_uri} <{ATLAS_NS}eventTimestamp> '
            f'"{event["event_timestamp"]}"^^<http://www.w3.org/2001/XMLSchema#dateTime> .'
        )

    # Link to customer (if present — household events may not have a customer_id)
    if event.get("customer_id"):
        customer_uri = f"<{INSTANCE_NS}customer-{event['customer_id']}>"
        triples.append(
            f'{event_uri} <{ATLAS_NS}relatedToCustomer> {customer_uri} .'
        )

    # Link to household (for household-aggregation events)
    if event.get("household_id"):
        household_uri = f"<{INSTANCE_NS}household-{event['household_id']}>"
        triples.append(
            f'{event_uri} <{ATLAS_NS}relatedToHousehold> {household_uri} .'
        )

    # Source attribution (which system produced this event)
    if event.get("source"):
        triples.append(
            f'{event_uri} <{ATLAS_NS}eventSource> '
            f'"{event["source"]}"^^<http://www.w3.org/2001/XMLSchema#string> .'
        )

    return "\n".join(triples)


def _signal_type_to_iri(signal_type: str) -> str:
    """Map a signal_type string to the corresponding SKOS concept IRI local name."""
    mapping = {
        "large-deposit-pattern": "LargeDepositPattern",
        "equity-event-signal": "EquityEventSignal",
        "retirement-rollover-signal": "RetirementRolloverSignal",
        "business-sale-liquidity-signal": "BusinessSaleLiquiditySignal",
        "household-aggregation-signal": "HouseholdAggregationSignal",
    }
    return mapping.get(signal_type, signal_type)


def write_to_lgd(triples_block: str) -> bool:
    """Write a block of N-Triples to the LGD via SPARQL UPDATE.

    Authenticates using SigV4 signing against the Neptune IAM auth endpoint.
    Returns True on success, False on failure.
    """
    if not LGD_ENDPOINT:
        print("ERROR: NEPTUNE_LGD_ENDPOINT not set")
        return False

    sparql_update = f"INSERT DATA {{\n{triples_block}\n}}"

    url = f"https://{LGD_ENDPOINT}:{LGD_PORT}/sparql"
    data = urllib.parse.urlencode({"update": sparql_update}).encode()

    # Sign the request with SigV4 for Neptune IAM auth
    credentials = _boto_session.get_credentials().get_frozen_credentials()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    request = AWSRequest(method="POST", url=url, headers=headers, data=data)
    SigV4Auth(credentials, "neptune-db", AWS_REGION).add_auth(request)

    # Neptune uses a certificate signed by the Amazon RDS CA. The system trust
    # store includes the Amazon Root CAs.
    ctx = ssl.create_default_context()

    req = urllib.request.Request(
        url,
        data=data,
        headers=dict(request.headers),
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return resp.status == 200
    except Exception as e:
        print(f"ERROR writing to LGD: {e}")
        return False


def handler(event, context):
    """Lambda handler for Kinesis/MSK event consumption.

    Processes a batch of records from the stream, converts each to RDF triples,
    and writes them to the LGD.

    Parameters
    ----------
    event : dict
        Lambda event payload containing 'Records' from Kinesis or MSK.
    context : object
        Lambda context (unused).

    Returns
    -------
    dict
        Batch processing result with success/failure counts.
    """
    records = event.get("Records", [])
    success_count = 0
    failure_count = 0

    for record in records:
        # Decode the record payload (base64 for Kinesis, plain for MSK)
        if "kinesis" in record:
            payload = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
        elif "value" in record:
            # MSK record
            payload = base64.b64decode(record["value"]).decode("utf-8")
        else:
            # Direct invocation (testing)
            payload = json.dumps(record)

        try:
            wealth_event = json.loads(payload)
            triples = event_to_triples(wealth_event)

            if write_to_lgd(triples):
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            print(f"ERROR processing record: {e}")
            failure_count += 1

    result = {
        "batchSize": len(records),
        "success": success_count,
        "failure": failure_count,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    print(f"Batch result: {json.dumps(result)}")
    return result
