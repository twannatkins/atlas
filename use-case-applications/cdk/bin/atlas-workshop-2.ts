#!/usr/bin/env node
/**
 * CDK app entry point for ATLAS Workshop 2.
 *
 * Single stack deployment. All constructs share the VPC, Cognito pool,
 * and cross-references between Lambda ARNs. Context parameters are
 * required — they come from Workshop 1's CloudFormation outputs.
 */

import * as cdk from "aws-cdk-lib";
import { AtlasWorkshop2Stack } from "../lib/atlas-workshop-2-stack";

const app = new cdk.App();

new AtlasWorkshop2Stack(app, "AtlasWorkshop2", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || "us-east-1",
  },
  description:
    "ATLAS Workshop 2 — Agents, MCP servers, AppSync, Cognito, CloudFront, Step Functions",
});
