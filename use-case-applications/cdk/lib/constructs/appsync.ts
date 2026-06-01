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
}

/** Inline Python for a proxy Lambda that forwards the AppSync event to an AgentCore Runtime. */
const PROXY_HANDLER = `
import boto3, json, os
RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
client = boto3.client("bedrock-agentcore")
def handler(event, context):
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        payload=json.dumps(event).encode(),
        contentType="application/json",
    )
    return json.loads(resp["response"].read())
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

    // ── Proxy Lambdas ────────────────────────────────────────────────────────
    // Each is a 10-line inline function. Code.fromInline avoids S3 asset upload
    // for trivially small functions and keeps the proxy pattern explicit in the
    // CDK source rather than in a separate file the reader has to find.

    const sparqlProxyFn = this.makeProxy("SparqlProxy", props.sparqlMcpArn);
    const registryProxyFn = this.makeProxy("RegistryProxy", props.registryMcpArn);
    const erProxyFn = this.makeProxy("ErProxy", props.erMcpArn);

    // ── Lambda datasources ───────────────────────────────────────────────────

    const sparqlDs = api.addLambdaDataSource("SparqlMcp", sparqlProxyFn);
    const registryDs = api.addLambdaDataSource("RegistryMcp", registryProxyFn);
    const erDs = api.addLambdaDataSource("ErMcp", erProxyFn);

    // ── Query resolvers ──────────────────────────────────────────────────────

    sparqlDs.createResolver("CustomerResolver", { typeName: "Query", fieldName: "customer" });
    sparqlDs.createResolver("HouseholdResolver", { typeName: "Query", fieldName: "household" });
    sparqlDs.createResolver("SearchCustomersResolver", { typeName: "Query", fieldName: "searchCustomers" });
    sparqlDs.createResolver("WealthSignalsResolver", { typeName: "Query", fieldName: "wealthSignals" });
    sparqlDs.createResolver("AdvisoryRelationshipsResolver", { typeName: "Query", fieldName: "advisoryRelationships" });
    sparqlDs.createResolver("ReferralsResolver", { typeName: "Query", fieldName: "referrals" });
    sparqlDs.createResolver("AuditTrailResolver", { typeName: "Query", fieldName: "auditTrail" });
    sparqlDs.createResolver("ThemesResolver", { typeName: "Query", fieldName: "themes" });
    registryDs.createResolver("CapabilitiesResolver", { typeName: "Query", fieldName: "capabilities" });
    erDs.createResolver("ResolveEntityResolver", { typeName: "Query", fieldName: "resolveEntity" });

    // ── Mutation resolvers ───────────────────────────────────────────────────

    registryDs.createResolver("RouteReferralResolver", { typeName: "Mutation", fieldName: "routeReferral" });
    registryDs.createResolver("DetectSignalsResolver", { typeName: "Mutation", fieldName: "detectSignals" });

    this.apiUrl = api.graphqlUrl;
  }

  /** Create a thin proxy Lambda pointing at a given AgentCore Runtime ARN. */
  private makeProxy(id: string, runtimeArn: string): lambda.Function {
    const fn = new lambda.Function(this, id, {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromInline(PROXY_HANDLER),
      timeout: cdk.Duration.seconds(30),
      environment: { AGENT_RUNTIME_ARN: runtimeArn },
    });

    fn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["bedrock-agentcore:InvokeAgentRuntime"],
      resources: [runtimeArn],
    }));

    return fn;
  }
}
