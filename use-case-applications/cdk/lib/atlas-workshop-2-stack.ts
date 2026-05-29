/**
 * ATLAS Workshop 2 — Main CDK Stack.
 *
 * Deploys the application layer on top of Workshop 1's Neptune cluster.
 * Organized as nested constructs, each owning a single concern.
 *
 * Does NOT deploy Neptune — that is Workshop 1's infrastructure.
 */

import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { NetworkingConstruct } from "./constructs/networking";
import { OntopConstruct } from "./constructs/ontop";
import { CognitoConstruct } from "./constructs/cognito";
import { AppSyncConstruct } from "./constructs/appsync";
import { LambdaConstruct } from "./constructs/lambdas";
import { CloudFrontConstruct } from "./constructs/cloudfront";
import { StepFunctionsConstruct } from "./constructs/step-functions";
import { LakeFormationConstruct } from "./constructs/lake-formation";
import { AgentCoreMemoryConstruct } from "./constructs/agentcore-memory";
import { AgentCoreRuntimesConstruct } from "./constructs/agentcore-runtimes";
import { OrchestratorRegistrationConstruct } from "./constructs/orchestrator-registration";

export class AtlasWorkshop2Stack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ─── Context parameters (from Workshop 1 CFN outputs) ───────────
    const neptuneEndpoint = this.node.tryGetContext("neptuneClusterEndpoint");
    const vpcId = this.node.tryGetContext("vpcId");
    const privateSubnetIds = this.node.tryGetContext("privateSubnetIds");

    if (!neptuneEndpoint || !vpcId) {
      cdk.Annotations.of(this).addWarning(
        "Missing context: neptuneClusterEndpoint and vpcId are required. " +
          "Pass them via --context or cdk.json.",
      );
    }

    // ─── 1. Networking ──────────────────────────────────────────────
    const networking = new NetworkingConstruct(this, "Networking", {
      vpcId,
      privateSubnetIds: privateSubnetIds?.split(",") || [],
    });

    // ─── 2. Ontop on ECS Fargate ────────────────────────────────────
    const ontop = new OntopConstruct(this, "Ontop", {
      vpc: networking.vpc,
      securityGroup: networking.ecsSecurityGroup,
      neptuneEndpoint,
    });

    // ─── 3. Cognito + IDC federation ────────────────────────────────
    const cognito = new CognitoConstruct(this, "Cognito");

    // ─── 4. Lambda deployments (5 step Lambdas for referral orchestrator) ──
    const lambdas = new LambdaConstruct(this, "Lambdas", {
      vpc: networking.vpc,
      securityGroup: networking.lambdaSecurityGroup,
    });

    // ─── 5. Step Functions state machine ────────────────────────────
    const stepFunctions = new StepFunctionsConstruct(this, "StepFunctions", {
      selectAdvisorFn: lambdas.getFunction("select-advisor"),
      validateRoutingFn: lambdas.getFunction("validate-routing"),
      writeRoutingDecisionFn: lambdas.getFunction("write-routing-decision"),
      notifyAdvisorFn: lambdas.getFunction("notify-advisor"),
      auditWriteFn: lambdas.getFunction("audit-write"),
    });

    // ─── 6. Register referral-orchestrator CUSTOM record ────────────
    // Must follow StepFunctions so stateMachineArn is a resolved token.
    new OrchestratorRegistrationConstruct(this, "OrchestratorRegistration", {
      stateMachineArn: stepFunctions.stateMachineArn,
    });

    // ─── 7. CloudFront distributions ────────────────────────────────
    const cloudfront = new CloudFrontConstruct(this, "CloudFront");

    // ─── 8. Lake Formation tag policies ─────────────────────────────
    new LakeFormationConstruct(this, "LakeFormation", {
      personas: cognito.personas,
    });

    // ─── 9. AgentCore Memory store ──────────────────────────────────
    const memory = new AgentCoreMemoryConstruct(this, "Memory");

    // ─── 10. AgentCore Runtimes (12 MCP-shaped components) ──────────
    // Runtimes before AppSync so Runtime ARNs are available for proxy Lambdas.
    const runtimes = new AgentCoreRuntimesConstruct(this, "Runtimes", {
      userPool: cognito.userPool,
      userPoolClient: cognito.userPoolClient,
      memory,
      neptuneSlgdEndpoint: neptuneEndpoint ?? "",
      neptuneLgdEndpoint: neptuneEndpoint ?? "",
      ontopEndpoint: ontop.endpoint,
    });

    // ─── 11. AppSync GraphQL API ────────────────────────────────────
    // AppSync is created last so the proxy Lambdas (defined inline below) can
    // reference Runtime ARNs as CDK tokens.
    const appsync = new AppSyncConstruct(this, "AppSync", {
      userPool: cognito.userPool,
      sparqlMcpArn: runtimes.atlasSparqlMcp.agentRuntimeArn,
      registryMcpArn: runtimes.atlasRegistryMcp.agentRuntimeArn,
      erMcpArn: runtimes.atlasErMcp.agentRuntimeArn,
    });

    // ─── Outputs ────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "AppSyncEndpoint", {
      value: appsync.apiUrl,
      description: "AppSync GraphQL endpoint URL",
    });
    new cdk.CfnOutput(this, "CognitoUserPoolId", {
      value: cognito.userPool.userPoolId,
      description: "Cognito User Pool ID",
    });
    new cdk.CfnOutput(this, "WholesaleUiUrl", {
      value: cloudfront.wholesaleUiUrl,
      description: "Wholesale UI CloudFront URL",
    });
    new cdk.CfnOutput(this, "OntopEndpoint", {
      value: ontop.endpoint,
      description: "Ontop internal ALB endpoint",
    });
    new cdk.CfnOutput(this, "StateMachineArn", {
      value: stepFunctions.stateMachineArn,
      description: "Referral orchestrator Step Functions ARN",
    });
    new cdk.CfnOutput(this, "MemoryId", {
      value: memory.memoryId,
      description: "AgentCore Memory store ID",
    });
    new cdk.CfnOutput(this, "AtlasSparqlMcpArn", {
      value: runtimes.atlasSparqlMcp.agentRuntimeArn,
      description: "atlas-sparql-mcp AgentCore Runtime ARN",
    });
    new cdk.CfnOutput(this, "ConversationalContextManagerArn", {
      value: runtimes.conversationalContextManager.agentRuntimeArn,
      description: "conversational-context-manager AgentCore Runtime ARN",
    });
  }
}
