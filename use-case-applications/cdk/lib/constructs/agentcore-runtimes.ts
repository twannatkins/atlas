/**
 * AgentCore Runtime construct — 12 MCP-shaped components.
 *
 * Deploys the 5 MCP servers and 7 standalone agents as AgentCore Runtime
 * instances. Each component's source directory is uploaded to a CDK-managed
 * S3 bucket at synth time via AgentRuntimeArtifact.fromCodeAsset.
 *
 * Entrypoint: ["main.py"]
 * AgentCore Runtime invokes main.py directly using its managed PYTHON_3_12 interpreter.
 * No launcher wrapper is needed. AgentCore provides native observability automatically
 * (per-invocation metrics, spans, CloudWatch Logs) — opentelemetry-instrument is an
 * optional enhancement for custom framework-level traces (e.g. LangGraph reasoning
 * steps), not required for baseline SR 11-7 audit coverage. If richer framework tracing
 * is desired in a future pass, bundle the ADOT distro via BundlingOptions + Docker or a
 * pre-built container image. See docs/deployment-findings.md.
 *
 * Authorization: RuntimeAuthorizerConfiguration.usingCognito wires the
 * Cognito user pool directly into AgentCore Identity validation. The Runtime
 * validates the JWT on every invocation; the persona claim is extracted and
 * available to the agent's execution context. See spec/11-identity-and-session.md.
 *
 * Environment variables: sourced from the JSON descriptors in
 * spec/04-aws-agent-registry/. Placeholder tokens like ${atlas_sparql_mcp_arn}
 * resolve to CDK token references at synth time.
 *
 * Memory: conversational-context-manager is the only Runtime that writes to
 * AgentCore Memory. Its execution role receives grantFullAccess from the Memory
 * construct (GetMemory/PutMemory/DeleteMemory). No other Runtime has Memory access.
 *
 * Runtime ordering: MCP servers first (their ARNs are referenced by agents),
 * then agents (in dependency order: nl-to-sparql-agent before
 * conversational-context-manager).
 *
 * referral-orchestrator is explicitly excluded — it is a Step Functions
 * workflow with a CUSTOM registry record, never an AgentCore Runtime.
 */

import * as path from "path";
import * as agentcore from "aws-cdk-lib/aws-bedrockagentcore";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as iam from "aws-cdk-lib/aws-iam";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { Construct } from "constructs";
import { AgentCoreMemoryConstruct } from "./agentcore-memory";

export interface AgentCoreRuntimesProps {
  readonly userPool: cognito.IUserPool;
  readonly userPoolClient: cognito.IUserPoolClient;
  readonly memory: AgentCoreMemoryConstruct;
  /** Resolved Neptune SLGD endpoint (from Workshop 1 CFN output). */
  readonly neptuneSlgdEndpoint: string;
  /** Resolved Neptune LGD endpoint (from Workshop 1 CFN output). */
  readonly neptuneLgdEndpoint: string;
  /** Resolved Ontop internal ALB endpoint. */
  readonly ontopEndpoint: string;
  /** Resolved Agent Registry endpoint URL. */
  readonly registryEndpoint?: string;
  /** S3 bucket name for ontology, prompt, and query artifacts (from WS1 CFN output). */
  readonly ontologyStagingBucket: string;
  /**
   * VPC to place the runtime ENIs in.
   * Required for the runtimes to reach Neptune in the private VPC.
   * VPC mode uses the existing NAT gateway for outbound Bedrock/S3 access.
   */
  readonly vpc: ec2.IVpc;
  /**
   * Private subnets where the runtime ENIs are placed.
   * Must be within the same VPC as Neptune. Neptune's SG allows 8182 from
   * the full VPC CIDR, so any ENI in these subnets can reach it without
   * additional SG rule changes.
   */
  readonly privateSubnets: ec2.ISubnet[];
  /**
   * ARN of the atlas-neptune-iam-auth managed policy from Workshop 1.
   * Grants neptune-db:ReadDataViaQuery + WriteDataViaQuery on both Neptune clusters.
   * Attached to each runtime execution role so the runtimes can query Neptune directly.
   * This is the long-tracked L1 gap: WS1 creates the policy but never attaches it.
   * Export name: atlas-neptune-iam-auth-policy (from atlas-neptune-twotier stack).
   */
  readonly neptuneIamAuthPolicyArn: string;
  /**
   * Pip-install requirements.txt into the runtime ZIP via Docker BundlingOptions.
   * Default false (the committed default ships raw source ZIPs — runtimes will NOT
   * start until deps are bundled). Set to true only in environments with a Docker
   * daemon available (e.g. local dev: pass -c bundleRuntimeDeps=true at deploy time).
   *
   * PUBLICATION BLOCKER: the portable fix is Option C — a scripts/build-runtimes.sh
   * that pip-installs to a ./build dir, zips, and uploads to the WS1 staging bucket,
   * then CDK references the ZIPs via fromS3. No Docker required at cdk synth.
   * Tracked in docs/deployment-findings.md.
   *
   * Why Docker bundling is self-biting for the published workshop: SageMaker Studio /
   * SageMaker Unified Studio notebook kernels have no Docker daemon — `cdk synth`
   * from within Studio would fail immediately when this flag is ON. The flag-OFF default
   * keeps the committed repo Studio-safe.
   */
  readonly bundleRuntimeDeps?: boolean;
  /**
   * Option C — portable pre-built runtime artifacts in S3 (the publication fix).
   *
   * When set (non-empty), each runtime sources its artifact from a pre-built ZIP at
   * s3://<ontologyStagingBucket>/<runtimeArtifactsS3Prefix>/<runtime-name>.zip via
   * AgentRuntimeArtifact.fromS3 — instead of fromCodeAsset. The ZIPs are produced and
   * uploaded out-of-band by scripts/build-runtimes.sh (pip install -t + zip + s3 cp),
   * so each ZIP already contains bedrock-agentcore and the runtime's other deps next
   * to main.py. CDK only references the S3 key, so NO Docker daemon is needed at synth
   * — this is the only path that is both Studio-safe AND ships working runtimes.
   *
   * <runtime-name> is the kebab-case basename of the component source dir
   * (e.g. "atlas-sparql-mcp", "nl-to-sparql-agent") — see RUNTIME_ARTIFACT_NAMES.
   *
   * Default undefined → fromCodeAsset behavior (raw or Docker) is byte-for-byte
   * unchanged. This flag takes precedence over bundleRuntimeDeps when both are set:
   * if pre-built S3 ZIPs are named, we use them and never invoke Docker.
   *
   * The staging bucket is the runner's own WS1 bucket (props.ontologyStagingBucket),
   * already a deploy-time input — Option C reuses it, creating no new bucket.
   */
  readonly runtimeArtifactsS3Prefix?: string;
}

// ["main.py"] is the correct no-OTEL entrypoint for fromCodeAsset: the managed
// PYTHON_3_12 runtime invokes main.py directly. System executables ("python",
// "python3") are rejected by AgentCore's server-side entrypoint validator. The
// CDK README shows ["opentelemetry-instrument","main.py"] as its example but OTEL
// is optional — AgentCore provides native CloudWatch observability automatically
// without it. See docs/deployment-findings.md for the entrypoint validation analysis.
const ENTRYPOINT = ["main.py"];
const PYTHON_3_12 = agentcore.AgentCoreRuntime.PYTHON_3_12;

/** Resolve the absolute path to a component source directory. */
function componentPath(relativeToUseCase: string): string {
  return path.join(__dirname, "..", "..", "..", relativeToUseCase);
}

/**
 * Derive the S3 object basename for a component's pre-built ZIP.
 * The key is "<runtimeArtifactsS3Prefix>/<basename>.zip" where basename is the
 * kebab-case source-dir name (e.g. "mcp-servers/atlas-sparql-mcp" → "atlas-sparql-mcp").
 * MUST stay in lockstep with scripts/build-runtimes.sh, which writes the same names.
 */
function artifactBasename(componentRelPath: string): string {
  return componentRelPath.split("/").pop() as string;
}

/**
 * Build an AgentRuntimeArtifact for a runtime. THREE packaging paths:
 *
 *   1. Option C (s3Prefix set) — fromS3: reference a pre-built ZIP at
 *      s3://<stagingBucket>/<s3Prefix>/<name>.zip. The ZIP (built by
 *      scripts/build-runtimes.sh) already contains bedrock-agentcore + deps next to
 *      main.py. NO Docker at synth. Studio-safe AND functional. Takes precedence.
 *   2. Docker bundling (bundleRuntimeDeps true) — fromCodeAsset + BundlingOptions:
 *      pip-install requirements.txt into the asset ZIP at synth. Requires a Docker
 *      daemon (local dev / CI only — unavailable in SageMaker Studio).
 *   3. Raw source (default) — fromCodeAsset with no bundling: ships source only.
 *      Runtimes provision green but crash on first invocation (the G3 gap) until
 *      deps are supplied via path 1 or 2. This is the byte-for-byte committed default.
 *
 * Paths 2 and 3 are unchanged from the original implementation; path 1 is additive.
 */
function makeArtifact(
  componentRelPath: string,
  bundleRuntimeDeps: boolean,
  stagingBucket: string,
  s3Prefix?: string,
): agentcore.AgentRuntimeArtifact {
  // ── Path 1: Option C — pre-built S3 ZIP (no Docker). Precedence over Docker. ──
  if (s3Prefix) {
    return agentcore.AgentRuntimeArtifact.fromS3(
      {
        bucketName: stagingBucket,
        objectKey: `${s3Prefix}/${artifactBasename(componentRelPath)}.zip`,
      },
      PYTHON_3_12,
      ENTRYPOINT,
    );
  }

  const assetPath = componentPath(componentRelPath);
  // ── Path 2: Docker bundling (unchanged) ──
  if (bundleRuntimeDeps) {
    return agentcore.AgentRuntimeArtifact.fromCodeAsset({
      path: assetPath,
      runtime: PYTHON_3_12,
      entrypoint: ENTRYPOINT,
      bundling: {
        // pip-install into /asset-output so all deps (bedrock-agentcore, rdflib, etc.)
        // are present when AgentCore executes main.py inside the microVM.
        image: lambda.Runtime.PYTHON_3_12.bundlingImage,
        command: [
          "bash", "-c",
          "pip install -r requirements.txt -t /asset-output --quiet && cp -r . /asset-output/",
        ],
      },
    });
  }
  // ── Path 3: raw source ZIP (unchanged default) ──
  return agentcore.AgentRuntimeArtifact.fromCodeAsset({
    path: assetPath,
    runtime: PYTHON_3_12,
    entrypoint: ENTRYPOINT,
  });
}

export class AgentCoreRuntimesConstruct extends Construct {
  // MCP servers
  public readonly atlasSparqlMcp: agentcore.Runtime;
  public readonly atlasShaclMcp: agentcore.Runtime;
  public readonly atlasErMcp: agentcore.Runtime;
  public readonly atlasFiboMcp: agentcore.Runtime;
  public readonly atlasRegistryMcp: agentcore.Runtime;

  // Agents
  public readonly nlToSparqlAgent: agentcore.Runtime;
  public readonly wealthSignalDetector: agentcore.Runtime;
  public readonly householdTraverser: agentcore.Runtime;
  public readonly referralRationaleDrafter: agentcore.Runtime;
  public readonly behavioralSignalAgent: agentcore.Runtime;
  public readonly themeSummarizer: agentcore.Runtime;
  public readonly conversationalContextManager: agentcore.Runtime;

  constructor(scope: Construct, id: string, props: AgentCoreRuntimesProps) {
    super(scope, id);

    const bundle = props.bundleRuntimeDeps ?? false;
    // Option C: when set, runtimes source pre-built ZIPs from the staging bucket via
    // fromS3 (no Docker). Threaded into every makeArtifact() call below. Undefined →
    // the existing fromCodeAsset paths (raw or Docker) are used, unchanged.
    const s3Prefix = props.runtimeArtifactsS3Prefix;
    const stagingBucket = props.ontologyStagingBucket;

    // VPC mode: place runtime ENIs in the private subnets so they can reach
    // Neptune on port 8182. Neptune's SG allows the full VPC CIDR at 8182,
    // so no additional ingress rule is needed. CDK auto-creates a dedicated
    // security group with allowAllOutbound=true — runtimes reach Bedrock and
    // S3 via the existing NAT gateway. VPC mode is the committed default (not
    // gated) because the runtimes must reach Neptune in every deployment.
    const networkConfig = agentcore.RuntimeNetworkConfiguration.usingVpc(this, {
      vpc: props.vpc,
      vpcSubnets: { subnets: props.privateSubnets },
    });

    // Option-A: the runtime authorizer is IAM/SigV4 (cut over in Pass 2d, verified live).
    // It moves in lockstep with the resolvers' MCP_AUTH_MODE (appsync.ts) — both read the
    // SAME flag, so they can never diverge.
    //   sigv4 (DEFAULT, live): runtimes authorize via IAM; callers (resolvers + the 7
    //          invoking agents) sign with SigV4 and hold bedrock-agentcore:InvokeAgentRuntime
    //          on the target ARNs.
    //   bearer (`-c mcpAuthMode=bearer`, the rollback): runtimes validate the user's Cognito
    //          JWT; resolvers forward it; the agent->MCP grants are omitted. This redeploy is
    //          byte-identical to the pre-cutover live template (Pass 1), so it is a safe revert.
    const mcpAuthMode =
      this.node.tryGetContext("mcpAuthMode") === "bearer" ? "bearer" : "sigv4";
    const authConfig =
      mcpAuthMode === "sigv4"
        ? agentcore.RuntimeAuthorizerConfiguration.usingIAM()
        : agentcore.RuntimeAuthorizerConfiguration.usingCognito(
            props.userPool,
            [props.userPoolClient],
          );

    // ── MCP Servers ──────────────────────────────────────────────────────────
    // atlasShaclMcp first: it has no peer dependencies, and atlasSparqlMcp
    // needs its ARN for the construct_and_validate operation.

    this.atlasShaclMcp = new agentcore.Runtime(this, "AtlasShaclMcp", {
      runtimeName: "atlas_shacl_mcp",
      description: "SHACL shape validation against the ATLAS ontology",
      agentRuntimeArtifact: makeArtifact("mcp-servers/atlas-shacl-mcp", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        SHAPES_S3_URI: `s3://${props.ontologyStagingBucket}/ontology/atlas-shapes.ttl`,
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-shacl-mcp" },
    });

    this.atlasSparqlMcp = new agentcore.Runtime(this, "AtlasSparqlMcp", {
      runtimeName: "atlas_sparql_mcp",
      description: "SPARQL query execution against Neptune SLGD/LGD and Ontop",
      agentRuntimeArtifact: makeArtifact("mcp-servers/atlas-sparql-mcp", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        NEPTUNE_SLGD_ENDPOINT: props.neptuneSlgdEndpoint,
        NEPTUNE_LGD_ENDPOINT: props.neptuneLgdEndpoint,
        ONTOP_ECS_ENDPOINT: props.ontopEndpoint,
        SHACL_MCP_ARN: this.atlasShaclMcp.agentRuntimeArn,
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-sparql-mcp" },
    });

    this.atlasErMcp = new agentcore.Runtime(this, "AtlasErMcp", {
      runtimeName: "atlas_er_mcp",
      description: "AWS Entity Resolution workflow invocation",
      agentRuntimeArtifact: makeArtifact("mcp-servers/atlas-er-mcp", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        ER_WORKFLOW_NAME: "atlas-entity-resolution",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-er-mcp" },
    });

    this.atlasFiboMcp = new agentcore.Runtime(this, "AtlasFiboMcp", {
      runtimeName: "atlas_fibo_mcp",
      description: "FIBO class and property lookup via atlas-sparql-mcp",
      agentRuntimeArtifact: makeArtifact("mcp-servers/atlas-fibo-mcp", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-fibo-mcp" },
    });

    this.atlasRegistryMcp = new agentcore.Runtime(this, "AtlasRegistryMcp", {
      runtimeName: "atlas_registry_mcp",
      description: "Agent Registry discovery and capability listing",
      agentRuntimeArtifact: makeArtifact("mcp-servers/atlas-registry-mcp", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        REGISTRY_ENDPOINT: props.registryEndpoint ?? "",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-registry-mcp" },
    });

    // ── Agents ───────────────────────────────────────────────────────────────

    this.nlToSparqlAgent = new agentcore.Runtime(this, "NlToSparqlAgent", {
      runtimeName: "nl_to_sparql_agent",
      description: "Translates natural-language questions into validated SPARQL",
      agentRuntimeArtifact: makeArtifact("agents/nl-to-sparql-agent", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        GROUND_TRUTH_S3_URI: `s3://${props.ontologyStagingBucket}/prompts/ground-truth.yaml`,
        PREFIXES_S3_URI: `s3://${props.ontologyStagingBucket}/prompts/prefixes.txt`,
        SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
        BEDROCK_EMBEDDING_MODEL_ID: "amazon.titan-embed-text-v2:0",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "nl-to-sparql-agent" },
    });

    this.wealthSignalDetector = new agentcore.Runtime(
      this,
      "WealthSignalDetector",
      {
        runtimeName: "wealth_signal_detector",
        description: "Detects wealth-event signals via SPARQL and SHACL validation",
        agentRuntimeArtifact: makeArtifact("agents/wealth-signal-detector", bundle, stagingBucket, s3Prefix),
        authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
        environmentVariables: {
          SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
          SHACL_MCP_ARN: this.atlasShaclMcp.agentRuntimeArn,
          SIGNAL_QUERIES_S3_URI: `s3://${props.ontologyStagingBucket}/queries/wealth-signals.yaml`,
        },
        tags: { Workshop: "atlas-workshop-2", Component: "wealth-signal-detector" },
      },
    );

    this.householdTraverser = new agentcore.Runtime(this, "HouseholdTraverser", {
      runtimeName: "household_traverser",
      description: "Traverses household membership and relationship graphs",
      agentRuntimeArtifact: makeArtifact("agents/household-traverser", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
      },
      tags: { Workshop: "atlas-workshop-2", Component: "household-traverser" },
    });

    this.referralRationaleDrafter = new agentcore.Runtime(
      this,
      "ReferralRationaleDrafter",
      {
        runtimeName: "referral_rationale_drafter",
        description: "Drafts probabilistic wealth-referral rationale for human review",
        agentRuntimeArtifact: makeArtifact("agents/referral-rationale-drafter", bundle, stagingBucket, s3Prefix),
        authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
        environmentVariables: {
          SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
          BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6",
          PROMPT_TEMPLATE_S3_URI:
            `s3://${props.ontologyStagingBucket}/prompts/referral-rationale.txt`,
        },
        tags: {
          Workshop: "atlas-workshop-2",
          Component: "referral-rationale-drafter",
        },
      },
    );

    this.behavioralSignalAgent = new agentcore.Runtime(
      this,
      "BehavioralSignalAgent",
      {
        runtimeName: "behavioral_signal_agent",
        description: "Detects behavioral anomaly signals via SPARQL and SHACL",
        agentRuntimeArtifact: makeArtifact("agents/behavioral-signal-agent", bundle, stagingBucket, s3Prefix),
        authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
        environmentVariables: {
          SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
          SHACL_MCP_ARN: this.atlasShaclMcp.agentRuntimeArn,
        },
        tags: {
          Workshop: "atlas-workshop-2",
          Component: "behavioral-signal-agent",
        },
      },
    );

    this.themeSummarizer = new agentcore.Runtime(this, "ThemeSummarizer", {
      runtimeName: "theme_summarizer",
      description: "Summarizes wealth themes as LLM-generated narrative for review",
      agentRuntimeArtifact: makeArtifact("agents/theme-summarizer", bundle, stagingBucket, s3Prefix),
      authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
      environmentVariables: {
        SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
        BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "theme-summarizer" },
    });

    // conversational-context-manager: last because it depends on nlToSparqlAgent ARN
    this.conversationalContextManager = new agentcore.Runtime(
      this,
      "ConversationalContextManager",
      {
        runtimeName: "conversational_context_manager",
        description: "Multi-turn conversation with AgentCore Memory persistence",
        agentRuntimeArtifact: makeArtifact("agents/conversational-context-manager", bundle, stagingBucket, s3Prefix),
        authorizerConfiguration: authConfig,
      networkConfiguration: networkConfig,
        environmentVariables: {
          NL_TO_SPARQL_AGENT_ARN: this.nlToSparqlAgent.agentRuntimeArn,
          AGENTCORE_MEMORY_NAMESPACE: "atlas-wealth-conv",
        },
        tags: {
          Workshop: "atlas-workshop-2",
          Component: "conversational-context-manager",
        },
      },
    );

    // Memory rollback-race fix: create Memory AFTER the 11 non-CCM runtimes so a
    // runtime-creation failure rolls back before Memory starts provisioning. AgentCore
    // Memory is slow to create and cannot be deleted mid-CREATING — a Memory caught
    // half-created during rollback orphans (billing). Ordering it last among the risky
    // resources prevents that. CCM is excluded from this dependency set because CCM's
    // IAM policy already depends on Memory (via grantFullAccess token), so adding
    // Memory → CCM would cycle. The 11-runtime ordering is safe and acyclic.
    // See docs/deployment-findings.md.
    const nonCcmRuntimes = [
      this.atlasShaclMcp, this.atlasSparqlMcp, this.atlasErMcp,
      this.atlasFiboMcp, this.atlasRegistryMcp, this.nlToSparqlAgent,
      this.wealthSignalDetector, this.householdTraverser,
      this.referralRationaleDrafter, this.behavioralSignalAgent,
      this.themeSummarizer,
    ];
    for (const runtime of nonCcmRuntimes) {
      props.memory.node.addDependency(runtime);
    }

    // conversational-context-manager is the only Runtime with Memory access
    props.memory.memory.grantFullAccess(this.conversationalContextManager);

    // Attach atlas-neptune-iam-auth to every runtime execution role so runtimes
    // can call Neptune with SigV4 IAM auth. This is the L1 fix for the long-tracked
    // gap: WS1 creates the policy but never attaches it to anything. Each attachment
    // gets a unique construct ID to avoid collisions.
    const neptunePolicy = iam.ManagedPolicy.fromManagedPolicyArn(
      this, "NeptuneIamAuthPolicy", props.neptuneIamAuthPolicyArn,
    );
    const allRuntimes = [
      this.atlasShaclMcp, this.atlasSparqlMcp, this.atlasErMcp,
      this.atlasFiboMcp, this.atlasRegistryMcp, this.nlToSparqlAgent,
      this.wealthSignalDetector, this.householdTraverser,
      this.referralRationaleDrafter, this.behavioralSignalAgent,
      this.themeSummarizer, this.conversationalContextManager,
    ];
    for (const runtime of allRuntimes) {
      runtime.role.addManagedPolicy(neptunePolicy);
    }

    // Option-A cutover (c): when the authorizer is IAM, the agents that call another
    // runtime (atlas-sparql-mcp or nl-to-sparql-agent) must be able to SigV4-invoke it.
    // Today there are ZERO such grants (the agent->MCP hop is dormant). This is gated on
    // the same mcpAuthMode flag so the default (bearer) deploy is byte-identical to live.
    // Scope: each agent role gets InvokeAgentRuntime on exactly the ARN(s) its code
    // invokes (see agents/*/[name].py) — sparql-mcp for the query-running agents,
    // nl-to-sparql-agent for the conversational manager.
    if (mcpAuthMode === "sigv4") {
      const sparqlMcpInvokers = [
        this.nlToSparqlAgent,        // nl_to_sparql_agent.py -> SPARQL_MCP_ARN
        this.wealthSignalDetector,   // -> SPARQL_MCP_ARN
        this.householdTraverser,     // -> SPARQL_MCP_ARN
        this.referralRationaleDrafter, // -> SPARQL_MCP_ARN
        this.behavioralSignalAgent,  // -> SPARQL_MCP_ARN
        this.themeSummarizer,        // -> SPARQL_MCP_ARN
      ];
      for (const agent of sparqlMcpInvokers) {
        agent.role.addToPrincipalPolicy(new iam.PolicyStatement({
          actions: ["bedrock-agentcore:InvokeAgentRuntime"],
          resources: [
            this.atlasSparqlMcp.agentRuntimeArn,
            `${this.atlasSparqlMcp.agentRuntimeArn}/*`,
          ],
        }));
      }
      // conversational-context-manager invokes nl-to-sparql-agent (not the MCP directly).
      this.conversationalContextManager.role.addToPrincipalPolicy(new iam.PolicyStatement({
        actions: ["bedrock-agentcore:InvokeAgentRuntime"],
        resources: [
          this.nlToSparqlAgent.agentRuntimeArn,
          `${this.nlToSparqlAgent.agentRuntimeArn}/*`,
        ],
      }));
    }
  }
}
