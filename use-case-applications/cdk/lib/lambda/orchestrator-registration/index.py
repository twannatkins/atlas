import boto3
import json
import os
import urllib.request

AGENT_NAME        = os.environ["AGENT_NAME"]
AGENT_DESCRIPTION = os.environ["AGENT_DESCRIPTION"]
AGENT_VERSION     = os.environ["AGENT_VERSION"]
REGISTRY_NAME     = os.environ["REGISTRY_NAME"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def cfn_send(event, context, status, data=None, reason=None, physical_id=None):
    body = json.dumps({
        "Status": status,
        "Reason": reason or status,
        "PhysicalResourceId": physical_id or event.get("PhysicalResourceId", AGENT_NAME),
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data or {},
    }).encode()
    url = event["ResponseURL"]
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "")
    urllib.request.urlopen(req)


def ensure_registry(client):
    """Return registryId for REGISTRY_NAME, creating the registry if absent.

    Uses get-or-create via ResourceNotFoundException rather than list_registries,
    which requires a newer botocore than the Lambda managed runtime bundles.
    """
    try:
        resp = client.get_registry(registryId=REGISTRY_NAME)
        return resp["registryId"]
    except client.exceptions.ResourceNotFoundException:
        create_resp = client.create_registry(
            name=REGISTRY_NAME,
            description="ATLAS Workshop 2 agent registry",
        )
        # registryArn: arn:aws:bedrock-agentcore:region:account:registry/{registryId}
        return create_resp["registryArn"].split("/")[-1]


def handler(event, context):
    request_type = event["RequestType"]
    client = boto3.client("bedrock-agentcore-control")
    try:
        if request_type in ("Create", "Update"):
            registry_id = ensure_registry(client)
            inline_content = json.dumps({
                "workflowArn": STATE_MACHINE_ARN,
                "workflowType": "StepFunctions",
                "agentName": AGENT_NAME,
                "version": AGENT_VERSION,
            })
            resp = client.create_registry_record(
                registryId=registry_id,
                name=AGENT_NAME,
                description=AGENT_DESCRIPTION,
                descriptorType="CUSTOM",
                descriptors={"custom": {"inlineContent": inline_content}},
                recordVersion=AGENT_VERSION,
            )
            record_arn = resp["recordArn"]
            cfn_send(event, context, "SUCCESS",
                     data={"RecordArn": record_arn},
                     physical_id=record_arn)
        elif request_type == "Delete":
            # PhysicalResourceId is the record ARN:
            # arn:aws:...:registry/{registryId}/record/{recordId}
            physical_id = event.get("PhysicalResourceId", "")
            parts = physical_id.split("/")
            if len(parts) >= 4:
                registry_id = parts[-3]
                record_id = parts[-1]
                try:
                    client.delete_registry_record(registryId=registry_id, recordId=record_id)
                except Exception:
                    pass  # idempotent — already deleted is fine
            cfn_send(event, context, "SUCCESS")
    except Exception as exc:
        cfn_send(event, context, "FAILED", reason=str(exc))
