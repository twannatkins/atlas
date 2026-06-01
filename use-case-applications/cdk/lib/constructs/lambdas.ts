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
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as path from "path";
import * as fs from "fs";
import { Construct } from "constructs";

export interface LambdaProps {
  vpc: ec2.IVpc;
  securityGroup: ec2.SecurityGroup;
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
        code: lambda.Code.fromAsset(sourceDir),
        timeout: cdk.Duration.seconds(30),
        memorySize: 512,
        vpc: props.vpc,
        securityGroups: [props.securityGroup],
      });
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
