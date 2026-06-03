/**
 * Cognito User Pool + IDC federation.
 *
 * Five groups corresponding to the five ATLAS personas. Cognito handles
 * application-layer permissions (Layer 2 of the four-layer model).
 * IDC handles identity (Layer 1).
 *
 * The OAuth callback URLs are environment-aware: localhost is only
 * included when the CDK context flag `includeLocalCallbacks` is true
 * (used during workshop development). Production deployments omit it.
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

export interface CognitoProps {
  /** The production callback URL (CloudFront distribution). */
  productionCallbackUrl?: string;
  /** Include http://localhost:3000/callback for local development. Default false. */
  includeLocalCallbacks?: boolean;
  /**
   * Enable USER_PASSWORD_AUTH on the app client. Default false (SRP-only).
   *
   * CAPSTONE-PROOF AFFORDANCE ONLY: enables fetching a real Cognito idToken
   * via `initiate-auth USER_PASSWORD_AUTH` for localStorage injection during
   * development verification. The published workshop default is SRP-only.
   * Enable only via CDK context (-c enableUserPasswordAuth=true) in a dev
   * account; never set to true in committed cdk.json or production config.
   */
  enableUserPasswordAuth?: boolean;
}

export class CognitoConstruct extends Construct {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly personas: string[];

  constructor(scope: Construct, id: string, props?: CognitoProps) {
    super(scope, id);

    this.personas = [...ATLAS_PERSONAS];

    // User Pool with custom persona attribute
    this.userPool = new cognito.UserPool(this, "UserPool", {
      // No hardcoded userPoolName — CDK auto-generates a stack-unique physical name.
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

    // Build callback URLs — localhost only included for local development
    const callbackUrls: string[] = [];
    if (props?.includeLocalCallbacks) {
      callbackUrls.push("http://localhost:3000/callback");
    }
    if (props?.productionCallbackUrl) {
      callbackUrls.push(props.productionCallbackUrl);
    } else {
      // Default production callback — replaced during deployment
      callbackUrls.push("https://atlas.example.com/callback");
    }

    // App client for the React UIs
    this.userPoolClient = this.userPool.addClient("WebClient", {
      authFlows: {
        userSrp: true,
        // USER_PASSWORD_AUTH: enabled only when enableUserPasswordAuth flag is set via
        // CDK context. Off by default — the published workshop uses SRP-only.
        userPassword: props?.enableUserPasswordAuth ?? false,
      },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
        callbackUrls,
      },
      generateSecret: false,
    });
  }
}
