/**
 * CloudFront distributions for the two React SPAs.
 *
 * Each distribution fronts an S3 origin bucket. Build artifacts are
 * deployed to S3 by CI; the CDK stack creates the bucket, distribution,
 * and Origin Access Control.
 */

import * as cdk from "aws-cdk-lib";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import { Construct } from "constructs";

export class CloudFrontConstruct extends Construct {
  public readonly wholesaleUiUrl: string;
  public readonly wealthUiUrl: string;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    // ── SPA sub-route rewrite (viewer-request CloudFront Function) ──────────────
    // The apps are Next.js output:"export" with trailingSlash:true, so each route is
    // its own document at <route>/index.html (e.g. out/callback/index.html). An S3
    // REST origin (OAC) returns 403 for a path with no exact object, so /callback and
    // /callback?code=… (Cognito's redirect target) 403 instead of serving the callback
    // document — the OAuth code is never exchanged.
    //
    // This function maps a clean route to its per-route index.html so the CORRECT
    // document loads. The querystring is NOT part of request.uri and CloudFront
    // forwards it unchanged, so ?code=… survives to the client-side handler
    // (callback-view.tsx reads it via useSearchParams).
    //
    // NOT a 403→/index.html SPA fallback: these apps export per-route HTML, so the
    // root document does not contain the callback handler — serving it for /callback
    // would drop the code. Path-preserving rewrite to the per-route document is required.
    //
    // Guard order (each URI class verified): "/" passes through (DefaultRootObject
    // serves index.html); a trailing-slash path gets index.html appended; a path whose
    // last segment has no "." (a route) gets /index.html appended; anything with a file
    // extension (/_next/static/*.js, *.css, favicon.ico) passes through untouched.
    const spaRewrite = new cloudfront.Function(this, "SpaRewriteFn", {
      comment: "Rewrite clean SPA routes to <route>/index.html; assets and query pass through.",
      code: cloudfront.FunctionCode.fromInline(`
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  if (uri === '/') {
    return request; // DefaultRootObject (index.html) handles the bare root
  }
  if (uri.endsWith('/')) {
    request.uri = uri + 'index.html';        // /callback/ -> /callback/index.html
    return request;
  }
  var lastSegment = uri.substring(uri.lastIndexOf('/') + 1);
  if (lastSegment.indexOf('.') === -1) {
    request.uri = uri + '/index.html';        // /callback -> /callback/index.html
  }
  // else: has a file extension (e.g. /_next/static/x.js) -> pass through untouched
  return request;
}
`),
    });

    const spaRewriteAssociation: cloudfront.FunctionAssociation[] = [
      { function: spaRewrite, eventType: cloudfront.FunctionEventType.VIEWER_REQUEST },
    ];

    // Wholesale UI (Phase 1)
    // No hardcoded bucketName — CDK auto-generates a stack-unique physical name,
    // which prevents bucket-name collisions when the stack is redeployed or when
    // multiple ATLAS stacks coexist in the same account.
    const wholesaleBucket = new s3.Bucket(this, "WholesaleBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const wholesaleDist = new cloudfront.Distribution(this, "WholesaleDist", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(wholesaleBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        functionAssociations: spaRewriteAssociation,
      },
      defaultRootObject: "index.html",
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html", // SPA fallback
        },
      ],
    });

    this.wholesaleUiUrl = `https://${wholesaleDist.distributionDomainName}`;

    // Wealth UI (Phase 2)
    const wealthBucket = new s3.Bucket(this, "WealthBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const wealthDist = new cloudfront.Distribution(this, "WealthDist", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(wealthBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        functionAssociations: spaRewriteAssociation,
      },
      defaultRootObject: "index.html",
      errorResponses: [
        {
          httpStatus: 404,
          responseHttpStatus: 200,
          responsePagePath: "/index.html",
        },
      ],
    });

    this.wealthUiUrl = `https://${wealthDist.distributionDomainName}`;
  }
}
