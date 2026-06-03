/**
 * Lambda deployments — 5 step Lambdas for the referral orchestrator.
 *
 * referral-orchestrator is a Step Functions workflow; its step Lambdas are
 * deployed from the referral-orchestrator source directory. The 12 MCP
 * servers and standalone agents run as AgentCore Runtimes instead
 * (see agentcore-runtimes.ts).
 *
 * Step Lambda names: select-advisor, validate-routing, write-routing-decision,
 * notify-advisor, audit-write. These are read from the referral-orchestrator
 * descriptor's runtime.step_lambdas array so the CDK stack stays in sync
 * with the spec without manual enumeration.
 */

import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as path from "path";
import * as fs from "fs";
import { Construct } from "constructs";

export interface LambdaProps {
  vpc: ec2.IVpc;
  securityGroup: ec2.SecurityGroup;
  /**
   * ARN of the atlas-neptune-iam-auth managed policy from WS1.
   * Grants neptune-db:ReadDataViaQuery + WriteDataViaQuery on both Neptune clusters.
   * The step Lambdas call Neptune directly (bypassing JWT-only AgentCore runtimes)
   * and need this policy to SigV4-sign their SPARQL requests.
   */
  neptuneIamAuthPolicyArn: string;
  /** Neptune SLGD cluster endpoint hostname (no port/protocol). */
  neptuneSlgdEndpoint: string;
  /** Neptune LGD cluster endpoint hostname. */
  neptuneLgdEndpoint: string;
  /** S3 URI of atlas-shapes.ttl for inline SHACL validation. */
  shapesS3Uri: string;
}

export class LambdaConstruct extends Construct {
  private functions: Map<string, lambda.Function> = new Map();

  constructor(scope: Construct, id: string, props: LambdaProps) {
    super(scope, id);

    const agentDir = path.join(
      __dirname, "..", "..", "..", "spec", "04-aws-agent-registry", "agents",
    );
    const agentSourceDir = path.join(__dirname, "..", "..", "..", "agents");

    if (!fs.existsSync(agentDir)) return;

    const files = fs.readdirSync(agentDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const descriptor = JSON.parse(
        fs.readFileSync(path.join(agentDir, file), "utf-8"),
      );
      if (descriptor.runtime?.type !== "step_functions") continue;
      this.deploySubLambdas(descriptor, agentSourceDir, descriptor.agent_name ?? "", props);
    }
  }

  private deploySubLambdas(
    descriptor: any,
    sourceBaseDir: string,
    name: string,
    props: LambdaProps,
  ): void {
    const stepLambdas: string[] = descriptor.runtime?.step_lambdas || [];
    const sourceDir = path.join(sourceBaseDir, name);

    for (const stepName of stepLambdas) {
      const handlerFile = stepName.replace(/-/g, "_");
      const fn = new lambda.Function(this, `Fn-${stepName}`, {
        // No hardcoded functionName — CDK auto-generates a stack-unique physical name.
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: `${handlerFile}.handler`,
        // Docker bundling installs requirements.txt (rdflib, pyshacl for validate-routing).
        // Same gated pattern as agentcore-runtimes — only runs when Docker is available.
        code: lambda.Code.fromAsset(sourceDir, {
          bundling: {
            image: lambda.Runtime.PYTHON_3_12.bundlingImage,
            command: [
              "bash", "-c",
              "pip install -r requirements.txt -t /asset-output --quiet && cp -r . /asset-output/",
            ],
          },
        }),
        timeout: cdk.Duration.seconds(30),
        memorySize: 512,
        vpc: props.vpc,
        securityGroups: [props.securityGroup],
        environment: {
          NEPTUNE_SLGD_ENDPOINT: props.neptuneSlgdEndpoint,
          NEPTUNE_LGD_ENDPOINT: props.neptuneLgdEndpoint,
          SHAPES_S3_URI: props.shapesS3Uri,
        },
      });

      // Attach atlas-neptune-iam-auth so step Lambdas can SigV4-sign Neptune requests.
      // The MCPs are JWT-only AgentCore runtimes (no IAM auth path); step Lambdas call
      // Neptune directly using SigV4 from this execution role.
      const neptunePolicy = iam.ManagedPolicy.fromManagedPolicyArn(
        this, `NeptunePolicy-${stepName}`, props.neptuneIamAuthPolicyArn,
      );
      fn.role?.addManagedPolicy(neptunePolicy);

      // validate-routing loads atlas-shapes.ttl from S3 for inline SHACL validation.
      fn.addToRolePolicy(new iam.PolicyStatement({
        actions: ["s3:GetObject"],
        resources: [`arn:aws:s3:::${props.shapesS3Uri.replace("s3://", "").split("/")[0]}/*`],
      }));

      // notify-advisor fires CloudWatch Events — add events:PutEvents if not already granted.
      if (stepName === "notify-advisor") {
        fn.addToRolePolicy(new iam.PolicyStatement({
          actions: ["events:PutEvents"],
          resources: ["*"],
        }));
      }

      this.functions.set(stepName, fn);
    }
  }

  public getFunction(name: string): lambda.Function {
    const fn = this.functions.get(name);
    if (!fn) {
      throw new Error(`Lambda function '${name}' not found in construct`);
    }
    return fn;
  }
}
