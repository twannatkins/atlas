/**
 * Lambda deployments — 5 step Lambdas for the referral orchestrator.
 *
 * referral-orchestrator is a Step Functions workflow; its step Lambdas are
 * deployed from the referral-orchestrator source directory. The 12 MCP
 * servers and standalone agents run as AgentCore Runtimes instead
 * (see agentcore-runtimes.ts).
 *
 * Step Lambda names: select-advisor, validate-routing, write-routing-decision,
 * notify-advisor, audit-write. These are read from the referral-orchestrator
 * descriptor's runtime.step_lambdas array so the CDK stack stays in sync
 * with the spec without manual enumeration.
 */

import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as path from "path";
import * as fs from "fs";
import { execSync } from "child_process";
import { Construct } from "constructs";

export interface LambdaProps {
  vpc: ec2.IVpc;
  securityGroup: ec2.SecurityGroup;
  /**
   * ARN of the atlas-neptune-iam-auth managed policy from WS1.
   * Grants neptune-db:ReadDataViaQuery + WriteDataViaQuery on both Neptune clusters.
   * The step Lambdas call Neptune directly (bypassing JWT-only AgentCore runtimes)
   * and need this policy to SigV4-sign their SPARQL requests.
   */
  neptuneIamAuthPolicyArn: string;
  /** Neptune SLGD cluster endpoint hostname (no port/protocol). */
  neptuneSlgdEndpoint: string;
  /** Neptune LGD cluster endpoint hostname. */
  neptuneLgdEndpoint: string;
  /** S3 URI of atlas-shapes.ttl for inline SHACL validation. */
  shapesS3Uri: string;
}

export class LambdaConstruct extends Construct {
  private functions: Map<string, lambda.Function> = new Map();

  constructor(scope: Construct, id: string, props: LambdaProps) {
    super(scope, id);

    const agentDir = path.join(
      __dirname, "..", "..", "..", "spec", "04-aws-agent-registry", "agents",
    );
    const agentSourceDir = path.join(__dirname, "..", "..", "..", "agents");

    if (!fs.existsSync(agentDir)) return;

    const files = fs.readdirSync(agentDir).filter((f) => f.endsWith(".json"));
    for (const file of files) {
      const descriptor = JSON.parse(
        fs.readFileSync(path.join(agentDir, file), "utf-8"),
      );
      if (descriptor.runtime?.type !== "step_functions") continue;
      this.deploySubLambdas(descriptor, agentSourceDir, descriptor.agent_name ?? "", props);
    }
  }

  private deploySubLambdas(
    descriptor: any,
    sourceBaseDir: string,
    name: string,
    props: LambdaProps,
  ): void {
    const stepLambdas: string[] = descriptor.runtime?.step_lambdas || [];
    const sourceDir = path.join(sourceBaseDir, name);

    for (const stepName of stepLambdas) {
      const handlerFile = stepName.replace(/-/g, "_");
      const fn = new lambda.Function(this, `Fn-${stepName}`, {
        // No hardcoded functionName — CDK auto-generates a stack-unique physical name.
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: `${handlerFile}.handler`,
        // Docker-free packaging (a clean SageMaker Studio kernel has no Docker daemon).
        // Only validate-routing imports third-party deps (rdflib + pyshacl, for inline
        // SHACL); the other four import only stdlib + boto3/botocore, BOTH of which the
        // Lambda Python 3.12 runtime already provides. So:
        //   - the four boto3-only Lambdas ship the source with NO dependency install
        //     (no-bundle fromAsset);
        //   - validate-routing installs its deps with a LOCAL bundler — rdflib==7.0.0
        //     and pyshacl==0.25.0 (and their full closure) are 100% py3-none-any wheels
        //     (no native code), so `pip install --target` is portable and needs no
        //     Docker. The Docker `image` stays only as an unused fallback for the rare
        //     host whose local pip can't satisfy the install.
        // assetHashType: SOURCE makes the asset hash derive from the source tree, not
        // the bundling output, so a re-synth on a different host yields the SAME hash —
        // closing the prior drift (the old `cp -r .` + unpinned boto3>= produced a new
        // hash every synth, showing phantom Lambda Modifies on every `cdk deploy`).
        code: this.packageStepLambda(stepName, sourceDir),
        timeout: cdk.Duration.seconds(30),
        memorySize: 512,
        vpc: props.vpc,
        securityGroups: [props.securityGroup],
        environment: {
          NEPTUNE_SLGD_ENDPOINT: props.neptuneSlgdEndpoint,
          NEPTUNE_LGD_ENDPOINT: props.neptuneLgdEndpoint,
          SHAPES_S3_URI: props.shapesS3Uri,
        },
      });

      // Attach atlas-neptune-iam-auth so step Lambdas can SigV4-sign Neptune requests.
      // The MCPs are JWT-only AgentCore runtimes (no IAM auth path); step Lambdas call
      // Neptune directly using SigV4 from this execution role.
      const neptunePolicy = iam.ManagedPolicy.fromManagedPolicyArn(
        this, `NeptunePolicy-${stepName}`, props.neptuneIamAuthPolicyArn,
      );
      fn.role?.addManagedPolicy(neptunePolicy);

      // validate-routing loads atlas-shapes.ttl from S3 for inline SHACL validation.
      fn.addToRolePolicy(new iam.PolicyStatement({
        actions: ["s3:GetObject"],
        resources: [`arn:aws:s3:::${props.shapesS3Uri.replace("s3://", "").split("/")[0]}/*`],
      }));

      // notify-advisor fires CloudWatch Events — add events:PutEvents if not already granted.
      if (stepName === "notify-advisor") {
        fn.addToRolePolicy(new iam.PolicyStatement({
          actions: ["events:PutEvents"],
          resources: ["*"],
        }));
      }

      this.functions.set(stepName, fn);
    }
  }

  /**
   * Package a step Lambda's code Docker-free.
   *
   * validate-routing is the only step Lambda with third-party imports (rdflib +
   * pyshacl). Its dependency closure is entirely py3-none-any (no native wheels), so a
   * plain `pip install --target` runs on any host — including a no-Docker Studio kernel.
   * We express that as a LOCAL bundler: CDK calls local.tryBundle() first and only falls
   * back to the Docker `image` if it returns false, so Docker is never invoked here.
   *
   * The other four step Lambdas import only stdlib + boto3/botocore (in-runtime), so they
   * ship as a no-bundle asset. Either way assetHashType is SOURCE → deterministic hash.
   */
  private packageStepLambda(stepName: string, sourceDir: string): lambda.AssetCode {
    if (stepName !== "validate-routing") {
      // No third-party deps — ship the source as-is (boto3/botocore are in the runtime).
      return lambda.Code.fromAsset(sourceDir, {
        assetHashType: cdk.AssetHashType.SOURCE,
      });
    }

    // validate-routing: install its pure-Python deps locally (no Docker), then copy the
    // source in alongside them.
    return lambda.Code.fromAsset(sourceDir, {
      assetHashType: cdk.AssetHashType.SOURCE,
      bundling: {
        // Unused fallback: CDK only reaches the Docker image if local.tryBundle returns
        // false. On a Studio kernel (local pip present) it never gets here.
        image: lambda.Runtime.PYTHON_3_12.bundlingImage,
        command: [
          "bash", "-c",
          "pip install -r requirements.txt -t /asset-output --quiet && cp -r . /asset-output/",
        ],
        local: {
          tryBundle(outputDir: string): boolean {
            try {
              // rdflib/pyshacl are py3-none-any → a host-local --target install is
              // portable (no manylinux/arch concerns). Pure-Python, so no Docker.
              execSync(
                `python3 -m pip install -r "${path.join(sourceDir, "requirements.txt")}" ` +
                  `--target "${outputDir}" --quiet --disable-pip-version-check`,
                { stdio: "inherit" },
              );
              // Copy the runtime source (handlers + neptune_client.py + atlas_sparql.py)
              // in next to the installed deps. Exclude test/dev-only files.
              for (const entry of fs.readdirSync(sourceDir)) {
                if (entry === "requirements.txt") continue;
                if (entry.startsWith("test_") || entry === "conftest.py") continue;
                const src = path.join(sourceDir, entry);
                if (fs.statSync(src).isFile()) {
                  fs.copyFileSync(src, path.join(outputDir, entry));
                }
              }
              return true;
            } catch (err) {
              // Local pip unavailable/failed — let CDK fall back to the Docker image.
              return false;
            }
          },
        },
      },
    });
  }

  public getFunction(name: string): lambda.Function {
    const fn = this.functions.get(name);
    if (!fn) {
      throw new Error(`Lambda function '${name}' not found in construct`);
    }
    return fn;
  }
}
