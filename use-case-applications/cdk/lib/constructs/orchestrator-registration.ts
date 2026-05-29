/**
 * OrchestratorRegistrationConstruct — CDK Custom Resource that registers
 * referral-orchestrator as a CUSTOM record in the Agent Registry at deploy time.
 *
 * Why a Custom Resource instead of a post-deploy script: the Step Functions
 * ARN is only available after the state machine is created. A Custom Resource
 * lets us pass the ARN as a CDK token reference at synth time and have it
 * resolve to the real ARN during the CloudFormation deploy, so the
 * registration is atomic with the rest of the stack.
 *
 * Control-plane service: bedrock-agentcore-control (not bedrock-agentcore).
 * The data-plane service (bedrock-agentcore) only exposes runtime operations
 * like InvokeAgentRuntime and SearchRegistryRecords. Registry management
 * (CreateRegistryRecord, DeleteRegistryRecord) lives on the control plane.
 * Both share the same IAM action prefix: bedrock-agentcore:.
 *
 * The provider Lambda:
 *   Create: ensures the atlas-workshop-2 registry exists (creates it if not
 *     found), then calls CreateRegistryRecord with descriptorType=CUSTOM and
 *     descriptors.custom.inlineContent set to the workflow payload JSON.
 *   Update: re-creates the record inline (CloudFormation replaces on ARN change).
 *   Delete: parses registryId and recordId from the stored PhysicalResourceId
 *     (the record ARN), then calls DeleteRegistryRecord.
 *
 * Caveat (DECISION 04-A): this Custom Resource code cannot be verified
 * end-to-end until Phase 05 deploys it. Phase 04 verifies only that
 * cdk synth succeeds and the IAM permissions are correct.
 */

import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as cr from "aws-cdk-lib/custom-resources";
import * as path from "path";
import * as fs from "fs";
import { Construct } from "constructs";

export interface OrchestratorRegistrationProps {
  /** Step Functions state machine ARN — resolved as a CDK token at synth time. */
  readonly stateMachineArn: string;
  /**
   * Agent Registry name to create or reuse.
   * @default "atlas-workshop-2"
   */
  readonly registryName?: string;
}

/** Inline Python for the Custom Resource provider Lambda. */
const PROVIDER_HANDLER = `
import boto3, json, os
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
    """Return registryId for REGISTRY_NAME, creating the registry if absent."""
    resp = client.list_registries()
    for reg in resp.get("registries", []):
        if reg["name"] == REGISTRY_NAME:
            return reg["registryId"]
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
`.trim();

export class OrchestratorRegistrationConstruct extends Construct {
  constructor(
    scope: Construct,
    id: string,
    props: OrchestratorRegistrationProps,
  ) {
    super(scope, id);

    const specPath = path.join(
      __dirname,
      "..",
      "..",
      "..",
      "spec",
      "04-aws-agent-registry",
      "agents",
      "referral-orchestrator.json",
    );
    const descriptor = JSON.parse(fs.readFileSync(specPath, "utf-8"));
    const registryName = props.registryName ?? "atlas-workshop-2";

    const providerFn = new lambda.Function(this, "ProviderFn", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromInline(PROVIDER_HANDLER),
      timeout: cdk.Duration.seconds(60),
      environment: {
        AGENT_NAME: descriptor.agent_name,
        AGENT_DESCRIPTION: descriptor.description,
        AGENT_VERSION: descriptor.version,
        REGISTRY_NAME: registryName,
        STATE_MACHINE_ARN: props.stateMachineArn,
      },
    });

    providerFn.addToRolePolicy(
      new iam.PolicyStatement({
        // bedrock-agentcore-control shares the bedrock-agentcore IAM namespace
        actions: [
          "bedrock-agentcore:ListRegistries",
          "bedrock-agentcore:CreateRegistry",
          "bedrock-agentcore:CreateRegistryRecord",
          "bedrock-agentcore:UpdateRegistryRecord",
          "bedrock-agentcore:DeleteRegistryRecord",
        ],
        resources: ["*"],
      }),
    );

    const provider = new cr.Provider(this, "Provider", {
      onEventHandler: providerFn,
    });

    new cdk.CustomResource(this, "Registration", {
      serviceToken: provider.serviceToken,
      resourceType: "Custom::AgentRegistryRecord",
      properties: {
        // Changing StateMachineArn triggers Update, which re-registers
        StateMachineArn: props.stateMachineArn,
      },
    });
  }
}
