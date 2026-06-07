/**
 * AppSync GraphQL API — FIBO-shaped schema with Cognito authorization.
 *
 * Schema is read from spec/05-appsync-graphql/schema.graphql.
 * Resolvers delegate to thin proxy Lambdas that forward the AppSync resolver
 * event to the corresponding AgentCore Runtime via InvokeAgentRuntime.
 * Authorization is by Cognito group claim — the persona flows through
 * to the resolver and on to the MCP server.
 *
 * Why proxy Lambdas instead of direct AppSync HTTP datasources: AppSync's
 * HTTP datasource requires VTL mapping templates and does not natively handle
 * the AgentCore InvokeAgentRuntime request/response envelope. A 10-line Lambda
 * is easier to teach than 40 lines of VTL and an HTTP endpoint config.
 */

import * as cdk from "aws-cdk-lib";
import * as appsync from "aws-cdk-lib/aws-appsync";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as path from "path";
import { Construct } from "constructs";

export interface AppSyncProps {
  userPool: cognito.UserPool;
  /** AgentCore Runtime ARN for atlas-sparql-mcp. */
  sparqlMcpArn: string;
  /** AgentCore Runtime ARN for atlas-registry-mcp. */
  registryMcpArn: string;
  /** AgentCore Runtime ARN for atlas-er-mcp. */
  erMcpArn: string;
  /** AgentCore Runtime ARN for nl-to-sparql-agent (#2 askGraph — direct-ARN invoke). */
  nlToSparqlArn: string;
  /** AgentCore Runtime ARN for referral-rationale-drafter (#3 draftRationale). */
  drafterArn: string;
  /** AgentCore Runtime ARN for conversational-context-manager (#5 converse — single-turn). */
  conversationalArn: string;
  /** s3://<bucket>/prompts/ground-truth.yaml — the agent's template source, read by
   *  suggestedQuestions so the UI's suggestions never drift from what the agent answers. */
  groundTruthS3Uri: string;
  /**
   * ARN of the referral-orchestrator Step Functions state machine.
   * routeReferral starts an execution here directly — the proven path. (The prior
   * registry invoke_capability → invoke_agent route used a non-existent boto3 method.)
   */
  stateMachineArn: string;
}

/**
 * Inline Python for a proxy Lambda that forwards the AppSync event to an AgentCore Runtime.
 *
 * Uses invoke_agent_runtime_for_user (OAuth/Cognito path) rather than invoke_agent_runtime
 * (SigV4/IAM path). The runtimes are configured with Cognito authorizer, so the caller must
 * forward the user's JWT. AppSync passes the raw Authorization header value in
 * event["identity"]["resolverContext"] — we extract it and pass it as the bearer token.
 */
/**
 * Inline Python for a proxy Lambda that forwards the AppSync event to an AgentCore Runtime.
 *
 * AgentCore runtimes configured with customJWTAuthorizer (Cognito) require the caller to
 * pass a Cognito ACCESS token (not idToken) as Bearer in a plain HTTPS POST — boto3's
 * invoke_agent_runtime uses SigV4 and cannot inject a custom Authorization header.
 * We use urllib instead to make the unsigned POST directly to the AgentCore data-plane
 * endpoint, forwarding the user's access token from the AppSync request header.
 *
 * The UI stores both idToken (atlas_token) and accessToken (atlas_access_token) in
 * localStorage. Apollo sends the access token in Authorization.
 */
const PROXY_HANDLER = `
import json, os, urllib.request
RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
import urllib.parse
ENCODED_ARN = urllib.parse.quote(RUNTIME_ARN, safe="")
ENDPOINT = f"https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{ENCODED_ARN}/invocations"
def handler(event, context):
    token = (event.get("request") or {}).get("headers", {}).get("authorization", "")
    body = json.dumps(event).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())
`.trim();

export class AppSyncConstruct extends Construct {
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: AppSyncProps) {
    super(scope, id);

    const schemaPath = path.join(
      __dirname, "..", "..", "..", "spec", "05-appsync-graphql", "schema.graphql",
    );

    const api = new appsync.GraphqlApi(this, "Api", {
      // Stack name appended so multiple ATLAS stacks in the same account don't collide.
      // AppSync allows duplicate display names but having a unique name aids debugging.
      name: `atlas-workshop-2-${cdk.Stack.of(this).stackName}`,
      definition: appsync.Definition.fromFile(schemaPath),
      authorizationConfig: {
        defaultAuthorization: {
          authorizationType: appsync.AuthorizationType.USER_POOL,
          userPoolConfig: { userPool: props.userPool },
        },
        additionalAuthorizationModes: [
          { authorizationType: appsync.AuthorizationType.IAM },
        ],
      },
      logConfig: {
        fieldLogLevel: appsync.FieldLogLevel.ERROR,
      },
    });

    // ── Resolver Lambdas ─────────────────────────────────────────────────────
    // Resolver logic lives in appsync-resolvers/{sparql,registry,er}-resolver/.
    // Each resolver dispatches on fieldName, builds the correct MCP payload,
    // calls the AgentCore runtime via HTTP (Bearer token forwarded from the
    // AppSync request headers), and shapes the response into GraphQL types.
    //
    // The original inline PROXY_HANDLER (forwarding raw AppSync events to the
    // AgentCore HTTP endpoint) was replaced here in commit [resolver-transport-fix]
    // because the MCP runtimes expect native MCP payloads, not AppSync events.
    // The written resolvers have the correct dispatch + shaping logic; only their
    // transport (lambda.invoke) was wrong — swapped to AgentCore HTTP.

    const resolverBase = path.join(__dirname, "..", "..", "..", "appsync-resolvers");

    // ── Option-A MCP auth mode (cut over to SigV4/IAM in Pass 2d) ──────────────
    // DEFAULT = "sigv4": the live, committed state after the Option-A cutover. Resolvers
    // invoke MCP via the boto3 SDK (SigV4, signed by the Lambda role), the runtime
    // authorizer is IAM (agentcore-runtimes.ts), and the IAM grant is InvokeAgentRuntime.
    // Verified live: the card reads the 2 signals via SigV4; dashboard non-null.
    //
    // Rollback to the pre-cutover behavior is `-c mcpAuthMode=bearer` (forward the user's
    // Cognito JWT + InvokeAgentRuntimeForUser, runtime authorizer Cognito). bearer and the
    // authorizer in agentcore-runtimes.ts read the SAME flag, so they always move together
    // — a redeploy with the flag is the provably-safe revert (Pass 1 proved bearer synth is
    // byte-identical to the pre-cutover live template).
    const mcpAuthMode = this.node.tryGetContext("mcpAuthMode") === "bearer" ? "bearer" : "sigv4";
    const mcpInvokeAction =
      mcpAuthMode === "sigv4"
        ? "bedrock-agentcore:InvokeAgentRuntime"
        : "bedrock-agentcore:InvokeAgentRuntimeForUser";
    // Inject MCP_AUTH_MODE=sigv4 (the default) into the resolver Lambdas; on a
    // `-c mcpAuthMode=bearer` rollback the env is omitted so the resolver code falls back
    // to its bearer default (sparql_resolver.MCP_AUTH_MODE defaults to "bearer").
    const mcpAuthEnv: Record<string, string> =
      mcpAuthMode === "sigv4" ? { MCP_AUTH_MODE: "sigv4" } : {};

    const sparqlProxyFn = new lambda.Function(this, "SparqlProxy", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "sparql_resolver.handler",
      code: lambda.Code.fromAsset(path.join(resolverBase, "sparql-resolver")),
      timeout: cdk.Duration.seconds(30),
      environment: { SPARQL_MCP_ARN: props.sparqlMcpArn, ...mcpAuthEnv },
    });
    sparqlProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: [mcpInvokeAction],
      resources: [`${props.sparqlMcpArn}*`],
    }));

    const registryProxyFn = new lambda.Function(this, "RegistryProxy", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "registry_resolver.handler",
      code: lambda.Code.fromAsset(path.join(resolverBase, "registry-resolver")),
      timeout: cdk.Duration.seconds(30),
      environment: {
        REGISTRY_MCP_ARN: props.registryMcpArn,
        // routeReferral starts this state machine directly (the proven path).
        STATE_MACHINE_ARN: props.stateMachineArn,
        // Action-side agents invoked DIRECTLY by ARN (askGraph / draftRationale / converse).
        NL_TO_SPARQL_ARN: props.nlToSparqlArn,
        DRAFTER_ARN: props.drafterArn,
        CONVERSATIONAL_ARN: props.conversationalArn,
        GROUND_TRUTH_S3_URI: props.groundTruthS3Uri,
        ...mcpAuthEnv,
      },
    });
    registryProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: [mcpInvokeAction],
      resources: [`${props.registryMcpArn}*`],
    }));
    // Option-A granted agent->MCP, but NOT this resolver->agent hop. askGraph/draftRationale
    // invoke nl-to-sparql-agent + referral-rationale-drafter DIRECTLY (the invoke_capability
    // indirection is broken — InvokeAgent is not a real op), so the registry-resolver role
    // needs InvokeAgentRuntime on those two agent ARNs. (When bearer, mcpInvokeAction is
    // InvokeAgentRuntimeForUser, matching the resolver's bearer transport.)
    registryProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: [mcpInvokeAction],
      resources: [`${props.nlToSparqlArn}*`, `${props.drafterArn}*`, `${props.conversationalArn}*`],
    }));
    // suggestedQuestions reads ground-truth.yaml from the staging bucket (read-only).
    registryProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["s3:GetObject"],
      resources: [`arn:aws:s3:::${props.groundTruthS3Uri.replace("s3://", "").split("/")[0]}/*`],
    }));
    // routeReferral → Step Functions StartExecution on the referral orchestrator.
    registryProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["states:StartExecution"],
      resources: [props.stateMachineArn],
    }));

    const erProxyFn = new lambda.Function(this, "ErProxy", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "er_resolver.handler",
      code: lambda.Code.fromAsset(path.join(resolverBase, "er-resolver")),
      timeout: cdk.Duration.seconds(30),
      // er_resolver calls both ER_MCP and SPARQL_MCP in sequence
      environment: {
        ER_MCP_ARN: props.erMcpArn,
        SPARQL_MCP_ARN: props.sparqlMcpArn,
        ...mcpAuthEnv,
      },
    });
    erProxyFn.addToRolePolicy(new iam.PolicyStatement({
      actions: [mcpInvokeAction],
      resources: [`${props.erMcpArn}*`, `${props.sparqlMcpArn}*`],
    }));

    // ── Lambda datasources ───────────────────────────────────────────────────

    const sparqlDs = api.addLambdaDataSource("SparqlMcp", sparqlProxyFn);
    const registryDs = api.addLambdaDataSource("RegistryMcp", registryProxyFn);
    const erDs = api.addLambdaDataSource("ErMcp", erProxyFn);

    // ── Query resolvers ──────────────────────────────────────────────────────

    sparqlDs.createResolver("CustomerResolver", { typeName: "Query", fieldName: "customer" });
    sparqlDs.createResolver("HouseholdResolver", { typeName: "Query", fieldName: "household" });
    sparqlDs.createResolver("SearchCustomersResolver", { typeName: "Query", fieldName: "searchCustomers" });
    sparqlDs.createResolver("WealthSignalsResolver", { typeName: "Query", fieldName: "wealthSignals" });
    // Nested Customer.wealthSignals — the schema declares it [WealthSignal!]! but it had
    // no resolver, so it returned null and nulled the whole parent (DASHBOARD_QUERY,
    // CUSTOMER_360_QUERY, CLIENT_360_QUERY). This resolver reuses the same sparql_resolver
    // Lambda; it dispatches on parentTypeName=="Customer" and scopes _resolve_wealth_signals
    // to the parent customer's uri (event.source.uri). Returns [] for no-signal customers.
    sparqlDs.createResolver("CustomerWealthSignalsResolver", { typeName: "Customer", fieldName: "wealthSignals" });
    sparqlDs.createResolver("AdvisoryRelationshipsResolver", { typeName: "Query", fieldName: "advisoryRelationships" });
    sparqlDs.createResolver("ReferralsResolver", { typeName: "Query", fieldName: "referrals" });
    sparqlDs.createResolver("AuditTrailResolver", { typeName: "Query", fieldName: "auditTrail" });
    sparqlDs.createResolver("ThemesResolver", { typeName: "Query", fieldName: "themes" });
    registryDs.createResolver("CapabilitiesResolver", { typeName: "Query", fieldName: "capabilities" });
    registryDs.createResolver("AskGraphResolver", { typeName: "Query", fieldName: "askGraph" });
    registryDs.createResolver("SuggestedQuestionsResolver", { typeName: "Query", fieldName: "suggestedQuestions" });
    erDs.createResolver("ResolveEntityResolver", { typeName: "Query", fieldName: "resolveEntity" });

    // ── Mutation resolvers ───────────────────────────────────────────────────

    registryDs.createResolver("RouteReferralResolver", { typeName: "Mutation", fieldName: "routeReferral" });
    registryDs.createResolver("DraftRationaleResolver", { typeName: "Mutation", fieldName: "draftRationale" });
    registryDs.createResolver("ConverseResolver", { typeName: "Mutation", fieldName: "converse" });

    this.apiUrl = api.graphqlUrl;
  }

}
