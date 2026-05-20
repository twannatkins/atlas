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

    // Wholesale UI (Phase 1)
    const wholesaleBucket = new s3.Bucket(this, "WholesaleBucket", {
      bucketName: `atlas-wholesale-ui-${cdk.Aws.ACCOUNT_ID}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const wholesaleDist = new cloudfront.Distribution(this, "WholesaleDist", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(wholesaleBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
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
      bucketName: `atlas-wealth-ui-${cdk.Aws.ACCOUNT_ID}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const wealthDist = new cloudfront.Distribution(this, "WealthDist", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(wealthBucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
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
