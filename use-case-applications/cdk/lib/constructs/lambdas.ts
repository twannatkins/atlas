/**
 * Lambda deployments — 13 handlers (5 MCP servers + 8 agents).
 *
 * IAM policies and environment variables are read from the JSON descriptors
 * in spec/04-aws-agent-registry/. The CDK stack does not hand-write policies —
 * the descriptors are the single source of truth.
 *
 * Placeholder tokens (${slgd_endpoint}, ${neptune_cluster_arn}, etc.) are
 * resolved to CDK token references at synth time.
 */

import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as path from "path";
import * as fs from "fs";
import { Construct } from "constructs";

export interface LambdaProps {
  vpc: ec2.IVpc;
  securityGroup: ec2.SecurityGroup;
  neptuneEndpoint: string;
  neptuneArn: string;
  ontopEndpoint: string;
  shapesBucket: string;
}

interface LambdaDescriptor {
  runtime: {
    handler: string;
    timeout_seconds: number;
    memory_mb: number;
    environment_variables: Record<string, string>;
  };
  iam_policy?: {
    inline_policy?: {
      Statement: Array<{
        Effect: string;
        Action: string[];
        Resource: string | string[];
      }>;
    };
  };
}

export class LambdaConstruct extends Construct {
  private functions: Map<string, lambda.Function> = new Map();

  constructor(scope: Construct, id: string, props: LambdaProps) {
    super(scope, id);

    const specDir = path.join(__dirname, "..", "..", "..", "spec", "04-aws-agent-registry");

    // Deploy MCP servers
    const mcpDir = path.join(specDir, "mcp-servers");
    const mcpSourceDir = path.join(__dirname, "..", "..", "..", "mcp-servers");
    this.deployFromDescriptors(mcpDir, mcpSourceDir, "mcp_server_name", props);

    // Deploy agents
    const agentDir = path.join(specDir, "agents");
    const agentSourceDir = path.join(__dirname, "..", "..", "..", "agents");
    this.deployFromDescriptors(agentDir, agentSourceDir, "agent_name", props);
  }

  /**
   * Read JSON descriptors from a spec directory and deploy Lambda functions.
   */
  private deployFromDescriptors(
    specSubDir: string,
    sourceBaseDir: string,
    nameField: string,
    props: LambdaProps,
  ): void {
    if (!fs.existsSync(specSubDir)) return;

    const files = fs.readdirSync(specSubDir).filter((f) => f.endsWith(".json"));

    for (const file of files) {
      const descriptor = JSON.parse(
        fs.readFileSync(path.join(specSubDir, file), "utf-8"),
      );
      const name: string = descriptor[nameField];
      if (!name) continue;

      // Skip non-Lambda runtimes (e.g., step_functions)
      if (descriptor.runtime?.type === "step_functions") {
        // Deploy sub-lambdas for orchestrator
        this.deploySubLambdas(descriptor, sourceBaseDir, name, props);
        continue;
      }
      if (descriptor.runtime?.type !== "lambda") continue;

      const sourceDir = path.join(sourceBaseDir, name);
      if (!fs.existsSync(sourceDir)) continue;

      const fn = this.createFunction(name, descriptor, sourceDir, props);
      this.functions.set(name, fn);
    }
  }

  /**
   * Deploy sub-Lambdas for the referral-orchestrator.
   */
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
        functionName: `referral-orchestrator-${stepName}`,
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

  /**
   * Create a single Lambda function from its descriptor.
   */
  private createFunction(
    name: string,
    descriptor: any,
    sourceDir: string,
    props: LambdaProps,
  ): lambda.Function {
    const runtime = descriptor.runtime;

    // Resolve environment variable placeholders
    const envVars = this.resolveEnvVars(
      runtime.environment_variables || {},
      props,
    );

    const fn = new lambda.Function(this, `Fn-${name}`, {
      functionName: name,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: runtime.handler,
      code: lambda.Code.fromAsset(sourceDir),
      timeout: cdk.Duration.seconds(runtime.timeout_seconds || 30),
      memorySize: runtime.memory_mb || 1024,
      environment: envVars,
      vpc: props.vpc,
      securityGroups: [props.securityGroup],
    });

    // Attach inline IAM policy from descriptor
    const inlinePolicy = descriptor.iam_policy?.inline_policy;
    if (inlinePolicy?.Statement) {
      for (const stmt of inlinePolicy.Statement) {
        const resources = Array.isArray(stmt.Resource)
          ? stmt.Resource
          : [stmt.Resource];
        fn.addToRolePolicy(
          new iam.PolicyStatement({
            effect:
              stmt.Effect === "Allow"
                ? iam.Effect.ALLOW
                : iam.Effect.DENY,
            actions: stmt.Action,
            resources: resources.map((r: string) =>
              this.resolveArnPlaceholder(r, props),
            ),
          }),
        );
      }
    }

    return fn;
  }

  /**
   * Resolve placeholder tokens in environment variables.
   */
  private resolveEnvVars(
    vars: Record<string, string>,
    props: LambdaProps,
  ): Record<string, string> {
    const resolved: Record<string, string> = {};
    for (const [key, value] of Object.entries(vars)) {
      resolved[key] = this.resolveToken(value, props);
    }
    return resolved;
  }

  /**
   * Resolve a single placeholder token to its CDK value.
   */
  private resolveToken(value: string, props: LambdaProps): string {
    return value
      .replace("${slgd_endpoint}", props.neptuneEndpoint)
      .replace("${lgd_endpoint}", props.neptuneEndpoint)
      .replace("${neptune_cluster_arn}", props.neptuneArn)
      .replace("${ontop_endpoint}", props.ontopEndpoint)
      .replace("${atlas_sparql_mcp_arn}", this.getFunctionArn("atlas-sparql-mcp"))
      .replace("${atlas_shacl_mcp_arn}", this.getFunctionArn("atlas-shacl-mcp"))
      .replace("${atlas_er_mcp_arn}", this.getFunctionArn("atlas-er-mcp"))
      .replace("${nl_to_sparql_agent_arn}", this.getFunctionArn("nl-to-sparql-agent"))
      .replace("${state_machine_arn}", "*") // Resolved after Step Functions construct
      .replace("${er_workflow_name}", "atlas-er-workflow")
      .replace("${agent_registry_endpoint}", "https://agentcore.us-east-1.amazonaws.com");
  }

  private resolveArnPlaceholder(arn: string, props: LambdaProps): string {
    return this.resolveToken(arn, props);
  }

  private getFunctionArn(name: string): string {
    const fn = this.functions.get(name);
    return fn ? fn.functionArn : `arn:aws:lambda:*:*:function:${name}`;
  }

  public getFunction(name: string): lambda.Function {
    const fn = this.functions.get(name);
    if (!fn) {
      throw new Error(`Lambda function '${name}' not found in construct`);
    }
    return fn;
  }
}
