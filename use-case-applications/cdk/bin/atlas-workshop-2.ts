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

// ATLAS Workshop 2 is pinned to us-east-1: the WS1 Neptune clusters, the Bedrock
// models, and the AgentCore runtimes are all provisioned in us-east-1. Deploying
// to any other region silently misses all of those dependencies. If CDK_DEFAULT_REGION
// is set to something other than us-east-1, fail fast with a clear message.
const region = process.env.CDK_DEFAULT_REGION || "us-east-1";
if (region !== "us-east-1") {
  throw new Error(
    `ATLAS Workshop 2 requires us-east-1 (CDK_DEFAULT_REGION="${region}"). ` +
    `The WS1 Neptune clusters, Bedrock models, and AgentCore runtimes are all ` +
    `provisioned in us-east-1. Unset CDK_DEFAULT_REGION or set it to "us-east-1".`
  );
}

new AtlasWorkshop2Stack(app, "AtlasWorkshop2", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region,
  },
  description:
    "ATLAS Workshop 2 — Agents, MCP servers, AppSync, Cognito, CloudFront, Step Functions",
});
