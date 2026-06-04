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
  /**
   * Additional OAuth callback URLs to register on the app client (e.g. both
   * CloudFront UI origins + localhost). Each must end in /callback. The hosted-UI
   * code flow rejects any redirect_uri not in this list, so every origin the UIs
   * are served from must be present. LogoutURLs mirror these (origin root).
   */
  callbackUrls?: string[];
  /**
   * Hosted-UI domain prefix (Cognito-managed domain). Required for the OAuth code
   * flow — without it there is no /oauth2/authorize or /oauth2/token endpoint.
   * Globally unique; resolves to https://<prefix>.auth.<region>.amazoncognito.com.
   */
  hostedUiDomainPrefix?: string;
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
  /** Hosted-UI domain base URL (https://<prefix>.auth.<region>.amazoncognito.com), if a domain was created. */
  public readonly hostedUiBaseUrl?: string;

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

    // Build callback URLs. Prefer the explicit list (both CloudFront origins +
    // localhost) passed by the stack; fall back to the legacy single-URL props so
    // existing behavior is preserved when no list is given.
    const callbackUrls: string[] = [];
    if (props?.callbackUrls && props.callbackUrls.length > 0) {
      callbackUrls.push(...props.callbackUrls);
    } else {
      if (props?.includeLocalCallbacks) {
        callbackUrls.push("http://localhost:3000/callback");
      }
      if (props?.productionCallbackUrl) {
        callbackUrls.push(props.productionCallbackUrl);
      } else {
        // Default production callback — replaced during deployment
        callbackUrls.push("https://atlas.example.com/callback");
      }
    }

    // LogoutURLs mirror the callback origins (root), so the hosted-UI /logout
    // endpoint can redirect back to each UI. Derived from the callback URLs by
    // stripping the /callback path.
    const logoutUrls = callbackUrls.map((u) => u.replace(/\/callback$/, "/"));

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
        logoutUrls,
      },
      generateSecret: false,
    });

    // Hosted-UI domain — REQUIRED for the OAuth code flow. Without a domain there is
    // no /oauth2/authorize or /oauth2/token endpoint, so a public SPA (no secret)
    // using PKCE has nowhere to send the user or exchange the code. The prefix is
    // globally unique; CDK creates an AWS::Cognito::UserPoolDomain.
    if (props?.hostedUiDomainPrefix) {
      this.userPool.addDomain("HostedUiDomain", {
        cognitoDomain: { domainPrefix: props.hostedUiDomainPrefix },
      });
      this.hostedUiBaseUrl = `https://${props.hostedUiDomainPrefix}.auth.${cdk.Stack.of(this).region}.amazoncognito.com`;

      // Surface the domain so the UI can build /oauth2/authorize (NEXT_PUBLIC_COGNITO_DOMAIN).
      new cdk.CfnOutput(this, "HostedUiDomain", {
        value: this.hostedUiBaseUrl,
        description: "Cognito hosted-UI base URL for the OAuth code flow",
      });
    }
  }
}
