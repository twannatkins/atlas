/**
 * Cognito User Pool + IDC federation.
 *
 * Five groups corresponding to the five ATLAS personas. Cognito handles
 * application-layer permissions (Layer 2 of the four-layer model).
 * IDC handles identity (Layer 1).
 */

import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { Construct } from "constructs";

export const ATLAS_PERSONAS = [
  "atlas-consumer-banker",
  "atlas-wealth-advisor",
  "atlas-bsa-analyst",
  "atlas-ontology-steward",
  "atlas-auditor",
] as const;

export class CognitoConstruct extends Construct {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly personas: string[];

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.personas = [...ATLAS_PERSONAS];

    // User Pool with custom persona attribute
    this.userPool = new cognito.UserPool(this, "UserPool", {
      userPoolName: "atlas-workshop-2",
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      customAttributes: {
        persona: new cognito.StringAttribute({ mutable: true }),
      },
      passwordPolicy: {
        minLength: 12,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY, // Workshop resource
    });

    // Create a group for each persona
    for (const persona of ATLAS_PERSONAS) {
      new cognito.CfnUserPoolGroup(this, `Group-${persona}`, {
        userPoolId: this.userPool.userPoolId,
        groupName: persona,
        description: `ATLAS persona: ${persona}`,
      });
    }

    // App client for the React UIs
    this.userPoolClient = this.userPool.addClient("WebClient", {
      authFlows: { userSrp: true },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
        callbackUrls: ["http://localhost:3000/callback", "https://atlas.example.com/callback"],
      },
      generateSecret: false,
    });
  }
}
