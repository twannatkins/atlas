/**
 * AppSync GraphQL API — FIBO-shaped schema with Cognito authorization.
 *
 * Schema is read from spec/05-appsync-graphql/schema.graphql.
 * Resolvers delegate to Lambda functions (MCP servers and agents).
 * Authorization is by Cognito group claim — the persona flows through
 * to the resolver, which passes it to the MCP server.
 */

import * as cdk from "aws-cdk-lib";
import * as appsync from "aws-cdk-lib/aws-appsync";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as path from "path";
import { Construct } from "constructs";
import { LambdaConstruct } from "./lambdas";

export interface AppSyncProps {
  userPool: cognito.UserPool;
  lambdas: LambdaConstruct;
}

export class AppSyncConstruct extends Construct {
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: AppSyncProps) {
    super(scope, id);

    const schemaPath = path.join(
      __dirname, "..", "..", "..", "spec", "05-appsync-graphql", "schema.graphql",
    );

    const api = new appsync.GraphqlApi(this, "Api", {
      name: "atlas-workshop-2",
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

    // Lambda data sources — each MCP server is a resolver backend
    const sparqlDs = api.addLambdaDataSource(
      "SparqlMcp",
      props.lambdas.getFunction("atlas-sparql-mcp"),
    );
    const registryDs = api.addLambdaDataSource(
      "RegistryMcp",
      props.lambdas.getFunction("atlas-registry-mcp"),
    );
    const erDs = api.addLambdaDataSource(
      "ErMcp",
      props.lambdas.getFunction("atlas-er-mcp"),
    );

    // Query resolvers — each delegates to the appropriate MCP server
    sparqlDs.createResolver("CustomerResolver", {
      typeName: "Query",
      fieldName: "customer",
    });
    sparqlDs.createResolver("HouseholdResolver", {
      typeName: "Query",
      fieldName: "household",
    });
    sparqlDs.createResolver("SearchCustomersResolver", {
      typeName: "Query",
      fieldName: "searchCustomers",
    });
    sparqlDs.createResolver("WealthSignalsResolver", {
      typeName: "Query",
      fieldName: "wealthSignals",
    });
    sparqlDs.createResolver("AdvisoryRelationshipsResolver", {
      typeName: "Query",
      fieldName: "advisoryRelationships",
    });
    sparqlDs.createResolver("ReferralsResolver", {
      typeName: "Query",
      fieldName: "referrals",
    });
    sparqlDs.createResolver("AuditTrailResolver", {
      typeName: "Query",
      fieldName: "auditTrail",
    });
    sparqlDs.createResolver("ThemesResolver", {
      typeName: "Query",
      fieldName: "themes",
    });
    registryDs.createResolver("CapabilitiesResolver", {
      typeName: "Query",
      fieldName: "capabilities",
    });
    erDs.createResolver("ResolveEntityResolver", {
      typeName: "Query",
      fieldName: "resolveEntity",
    });

    // Mutation resolvers — go through the registry for audit trail
    registryDs.createResolver("RouteReferralResolver", {
      typeName: "Mutation",
      fieldName: "routeReferral",
    });
    registryDs.createResolver("DetectSignalsResolver", {
      typeName: "Mutation",
      fieldName: "detectSignals",
    });

    this.apiUrl = api.graphqlUrl;
  }
}
