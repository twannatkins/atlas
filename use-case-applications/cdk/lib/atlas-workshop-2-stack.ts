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
// DEFERRED: LakeFormationConstruct requires account-level LF-admin grant.
// import { LakeFormationConstruct } from "./constructs/lake-formation";
import { AgentCoreMemoryConstruct } from "./constructs/agentcore-memory";
import { AgentCoreRuntimesConstruct } from "./constructs/agentcore-runtimes";
import { OrchestratorRegistrationConstruct } from "./constructs/orchestrator-registration";

export class AtlasWorkshop2Stack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ─── Context parameters (from Workshop 1 CFN outputs) ───────────
    const neptuneEndpoint = this.node.tryGetContext("neptuneClusterEndpoint");
    // neptuneLgdEndpoint defaults to the SLGD endpoint when not supplied so the
    // stack still synthesizes, but behavioral-signal-agent needs the real LGD
    // endpoint to query session-level data. Provide it via cdk.json or --context.
    const neptuneLgdEndpoint =
      this.node.tryGetContext("neptuneLgdEndpoint") ?? neptuneEndpoint;
    const vpcId = this.node.tryGetContext("vpcId");
    const privateSubnetIds = this.node.tryGetContext("privateSubnetIds");
    const ontologyStagingBucket = this.node.tryGetContext("ontologyStagingBucket") ?? "";

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
    const cognito = new CognitoConstruct(this, "Cognito", {
      // enableUserPasswordAuth: capstone-proof affordance only. Pass -c enableUserPasswordAuth=true
      // at deploy time for dev token-injection testing. Default false (SRP-only published default).
      enableUserPasswordAuth:
        this.node.tryGetContext("enableUserPasswordAuth") === "true",
      // Hosted-UI domain for the OAuth code flow (DRIFT-2). Prefix is globally unique;
      // overridable via -c cognitoDomainPrefix=. Default is account-scoped + deterministic
      // so teardown can target it. Resolves to
      // https://<prefix>.auth.us-east-1.amazoncognito.com.
      hostedUiDomainPrefix:
        this.node.tryGetContext("cognitoDomainPrefix") ?? `atlas-ws2-${this.account}`,
      // OAuth callback URLs registered on the Cognito app client. These must be the
      // origins the UIs are served from, but a CloudFront distribution's domain is not
      // known until the FIRST deploy creates it — a chicken-and-egg. So the two-pass
      // flow (see spec/02-prerequisites.md "Set these once"):
      //   1. First deploy with no override -> only localhost is registered (the
      //      distributions are created in this same deploy; their URLs are now in the
      //      WholesaleUiUrl / WealthUiUrl stack outputs).
      //   2. Redeploy with -c uiCallbackUrls=https://<wholesale>/callback,
      //      https://<wealth>/callback,http://localhost:3000/callback
      // There is intentionally NO hardcoded CloudFront default — a baked-in domain
      // would register THIS author's distributions on a clean account's pool.
      callbackUrls: (
        this.node.tryGetContext("uiCallbackUrls") as string | undefined
      )?.split(",") ?? [
        "http://localhost:3000/callback", // local dev only until you supply -c uiCallbackUrls=
      ],
    });

    // ─── 4. Lambda deployments (5 step Lambdas for referral orchestrator) ──
    const lambdas = new LambdaConstruct(this, "Lambdas", {
      vpc: networking.vpc,
      securityGroup: networking.lambdaSecurityGroup,
      // Step Lambdas call Neptune directly (JWT-only AgentCore runtimes have no SigV4 path).
      neptuneIamAuthPolicyArn: cdk.Fn.importValue("atlas-neptune-iam-auth-policy"),
      neptuneSlgdEndpoint: neptuneEndpoint ?? "",
      neptuneLgdEndpoint: neptuneLgdEndpoint ?? "",
      shapesS3Uri: `s3://${ontologyStagingBucket}/ontology/atlas-shapes.ttl`,
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
    const orchestratorRegistration = new OrchestratorRegistrationConstruct(this, "OrchestratorRegistration", {
      stateMachineArn: stepFunctions.stateMachineArn,
    });

    // ─── 7. CloudFront distributions ────────────────────────────────
    const cloudfront = new CloudFrontConstruct(this, "CloudFront");

    // ─── 8. Lake Formation tag policies ─────────────────────────────
    // DEFERRED: Lake Formation tags require account-level LF-admin grant
    //   (lakeformation:CreateLFTag on the catalog), which is a WS0 foundation
    //   prerequisite — a runner's fresh account won't have it either. Not exercised
    //   in the Phase 1 referral capstone. Re-enable once the foundation template
    //   grants the CDK CloudFormation execution role LF data-lake-administrator rights
    //   via put-data-lake-settings. See docs/ws0-foundation-spec.md.
    // new LakeFormationConstruct(this, "LakeFormation", {
    //   personas: cognito.personas,
    // });

    // ─── 9. AgentCore Memory store ──────────────────────────────────
    // Memory rollback-race fix (2nd edge): Memory also depends on OrchestratorRegistration
    // so it starts only after the custom resource Lambda completes successfully. Without
    // this, a fast-failing OrchestratorRegistration can trigger rollback while Memory is
    // still mid-CREATING (~90s window), orphaning it. See docs/deployment-findings.md.
    const memory = new AgentCoreMemoryConstruct(this, "Memory");
    memory.node.addDependency(orchestratorRegistration);

    // ─── 10. AgentCore Runtimes (12 MCP-shaped components) ──────────
    // Runtimes before AppSync so Runtime ARNs are available for proxy Lambdas.
    const runtimes = new AgentCoreRuntimesConstruct(this, "Runtimes", {
      userPool: cognito.userPool,
      userPoolClient: cognito.userPoolClient,
      memory,
      neptuneSlgdEndpoint: neptuneEndpoint ?? "",
      neptuneLgdEndpoint: neptuneLgdEndpoint ?? "",
      ontopEndpoint: ontop.endpoint,
      ontologyStagingBucket,
      // VPC mode — committed default so runtimes can reach Neptune in the private VPC.
      // The existing NAT gateway keeps Bedrock/S3 reachable from private subnets.
      vpc: networking.vpc,
      privateSubnets: networking.privateSubnets,
      // atlas-neptune-iam-auth managed policy from WS1 — grants ReadDataViaQuery +
      // WriteDataViaQuery on both Neptune clusters. Attached to each runtime execution
      // role so runtimes can query Neptune with SigV4 IAM auth.
      neptuneIamAuthPolicyArn: cdk.Fn.importValue("atlas-neptune-iam-auth-policy"),
      // Docker bundling: opt-in for environments with Docker at synth time.
      // Default false — committed repo stays Studio-safe (no Docker daemon in Studio kernels).
      // Pass -c bundleRuntimeDeps=true to enable for local dev / CI.
      bundleRuntimeDeps:
        this.node.tryGetContext("bundleRuntimeDeps") === "true",
      // Option C — portable pre-built dependency ZIPs in S3 (no Docker at synth).
      // When set (non-empty), runtimes source their artifact from
      // s3://<ontologyStagingBucket>/<prefix>/<runtime-name>.zip via fromS3 instead of
      // fromCodeAsset. This is the Studio-safe way to ship runtimes WITH their deps:
      // scripts/build-runtimes.sh pip-installs + zips + uploads each runtime, and CDK
      // just references the S3 key — no Docker daemon required at `cdk synth`.
      // Default unset (undefined) → existing fromCodeAsset behavior is byte-for-byte
      // unchanged. Pass -c runtimeArtifactsS3Prefix=runtimes after running the build script.
      runtimeArtifactsS3Prefix:
        this.node.tryGetContext("runtimeArtifactsS3Prefix") || undefined,
    });

    // ─── 11. AppSync GraphQL API ────────────────────────────────────
    // AppSync is created last so the proxy Lambdas (defined inline below) can
    // reference Runtime ARNs as CDK tokens.
    const appsync = new AppSyncConstruct(this, "AppSync", {
      userPool: cognito.userPool,
      sparqlMcpArn: runtimes.atlasSparqlMcp.agentRuntimeArn,
      registryMcpArn: runtimes.atlasRegistryMcp.agentRuntimeArn,
      erMcpArn: runtimes.atlasErMcp.agentRuntimeArn,
      // Action-side agents (#2 askGraph, #3 draftRationale) — invoked directly by ARN.
      nlToSparqlArn: runtimes.nlToSparqlAgent.agentRuntimeArn,
      drafterArn: runtimes.referralRationaleDrafter.agentRuntimeArn,
      groundTruthS3Uri: `s3://${ontologyStagingBucket}/prompts/ground-truth.yaml`,
      // routeReferral starts this state machine directly (proven path).
      stateMachineArn: stepFunctions.stateMachineArn,
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
    new cdk.CfnOutput(this, "WealthUiUrl", {
      value: cloudfront.wealthUiUrl,
      description: "Wealth UI CloudFront URL",
    });
    // Deploy-runbook keystone (clean-account UI deploy). The two CloudFront origin
    // buckets have no hardcoded name — CDK generates a stack-unique physical name — so
    // a runner has no way to discover the `aws s3 sync out/ s3://<bucket>` target
    // without these outputs. Surfacing them closes deploy-gap G1.
    new cdk.CfnOutput(this, "WholesaleBucketName", {
      value: cloudfront.wholesaleBucketName,
      description: "S3 origin bucket for the Wholesale UI — sync `next build` out/ here",
    });
    new cdk.CfnOutput(this, "WealthBucketName", {
      value: cloudfront.wealthBucketName,
      description: "S3 origin bucket for the Wealth UI — sync `next build` out/ here",
    });
    // The UI .env.local needs the app-client id (NEXT_PUBLIC_COGNITO_CLIENT_ID). The
    // stack previously output only CognitoUserPoolId, so docs referencing
    // CognitoUserPoolWebClientId resolved to nothing. Closes deploy-gap G4 (client id).
    new cdk.CfnOutput(this, "CognitoUserPoolWebClientId", {
      value: cognito.userPoolClient.userPoolClientId,
      description: "Cognito app-client id for the UIs (NEXT_PUBLIC_COGNITO_CLIENT_ID)",
    });
    // Hosted-UI base URL (NEXT_PUBLIC_COGNITO_DOMAIN). Emitted here at stack level with
    // a clean key; previously emitted inside CognitoConstruct, where CDK appended a hash
    // (CognitoHostedUiDomain<hash>) so an exact-key lookup for "CognitoHostedUiDomain"
    // failed. Closes deploy-gap G4 (hosted-UI domain key).
    new cdk.CfnOutput(this, "CognitoHostedUiDomain", {
      value: cognito.hostedUiBaseUrl ?? "",
      description: "Cognito hosted-UI base URL for the OAuth code flow (NEXT_PUBLIC_COGNITO_DOMAIN)",
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
