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

/** Path to the bundled Lambda asset directory. */
const HANDLER_ASSET_PATH = path.join(__dirname, "..", "lambda", "orchestrator-registration");

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
      // fromAsset + Docker bundling ensures boto3>=1.43 (which includes
      // bedrock-agentcore-control) is present. Lambda's managed Python 3.12
      // runtime bundles an older botocore that predates this service.
      code: lambda.Code.fromAsset(HANDLER_ASSET_PATH, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_12.bundlingImage,
          command: [
            "bash", "-c",
            "pip install -r requirements.txt -t /asset-output && cp index.py /asset-output/",
          ],
        },
      }),
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
          "bedrock-agentcore:GetRegistry",
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
