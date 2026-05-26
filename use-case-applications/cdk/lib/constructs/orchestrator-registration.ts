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
 * The provider Lambda calls bedrock-agentcore:CreateAgent on Create/Update
 * and bedrock-agentcore:DeleteAgent on Delete. The registration payload is
 * passed via environment variables so the Lambda code itself is static and
 * can use Code.fromInline.
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
}

/** Inline Python for the Custom Resource provider Lambda. */
const PROVIDER_HANDLER = `
import boto3, json, os
import urllib.request

AGENT_NAME        = os.environ["AGENT_NAME"]
AGENT_DESCRIPTION = os.environ["AGENT_DESCRIPTION"]
AGENT_VERSION     = os.environ["AGENT_VERSION"]
INPUT_SCHEMA      = json.loads(os.environ["INPUT_SCHEMA_JSON"])
OUTPUT_SCHEMA     = json.loads(os.environ["OUTPUT_SCHEMA_JSON"])
REGISTRY_META     = json.loads(os.environ["REGISTRY_META_JSON"])
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

def cfn_send(event, context, status, data=None, reason=None):
    body = json.dumps({
        "Status": status,
        "Reason": reason or status,
        "PhysicalResourceId": event.get("PhysicalResourceId", AGENT_NAME),
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": data or {},
    }).encode()
    url = event["ResponseURL"]
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "")
    urllib.request.urlopen(req)

def handler(event, context):
    request_type = event["RequestType"]
    client = boto3.client("bedrock-agentcore")
    try:
        if request_type in ("Create", "Update"):
            meta = dict(REGISTRY_META)
            meta["workflowArn"] = STATE_MACHINE_ARN
            resp = client.create_agent(
                agentName=AGENT_NAME,
                description=AGENT_DESCRIPTION,
                version=AGENT_VERSION,
                inputSchema=INPUT_SCHEMA,
                outputSchema=OUTPUT_SCHEMA,
                registryMetadata=meta,
            )
            cfn_send(event, context, "SUCCESS",
                     data={"AgentId": resp.get("agentId", "")})
        elif request_type == "Delete":
            agent_id = event.get("PhysicalResourceId", "")
            if agent_id and agent_id != AGENT_NAME:
                client.delete_agent(agentId=agent_id)
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

    // Provider Lambda — runs on Create, Update, Delete
    const providerFn = new lambda.Function(this, "ProviderFn", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromInline(PROVIDER_HANDLER),
      timeout: cdk.Duration.seconds(60),
      environment: {
        AGENT_NAME: descriptor.agent_name,
        AGENT_DESCRIPTION: descriptor.description,
        AGENT_VERSION: descriptor.version,
        INPUT_SCHEMA_JSON: JSON.stringify(descriptor.input_schema),
        OUTPUT_SCHEMA_JSON: JSON.stringify(descriptor.output_schema),
        REGISTRY_META_JSON: JSON.stringify(descriptor.registry_metadata),
        STATE_MACHINE_ARN: props.stateMachineArn,
      },
    });

    providerFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock-agentcore:CreateAgent",
          "bedrock-agentcore:UpdateAgent",
          "bedrock-agentcore:DeleteAgent",
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
        // Force re-registration on state machine ARN change
        StateMachineArn: props.stateMachineArn,
      },
    });
  }
}
