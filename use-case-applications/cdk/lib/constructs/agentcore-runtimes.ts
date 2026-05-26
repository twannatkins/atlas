/**
 * AgentCore Runtime construct — 12 MCP-shaped components.
 *
 * Deploys the 5 MCP servers and 7 standalone agents as AgentCore Runtime
 * instances. Each component's source directory is uploaded to a CDK-managed
 * S3 bucket at synth time via AgentRuntimeArtifact.fromCodeAsset.
 *
 * Entrypoint: ["opentelemetry-instrument", "main.py"]
 * AWS Distro for OpenTelemetry instruments every invocation automatically.
 * Execution traces appear in CloudWatch Transaction Search without
 * per-handler instrumentation code.
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
}

const ENTRYPOINT = ["opentelemetry-instrument", "main.py"];
const PYTHON_3_12 = agentcore.AgentCoreRuntime.PYTHON_3_12;

/** Resolve the absolute path to a component source directory. */
function componentPath(relativeToUseCase: string): string {
  return path.join(__dirname, "..", "..", "..", relativeToUseCase);
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

    const authConfig = agentcore.RuntimeAuthorizerConfiguration.usingCognito(
      props.userPool,
      [props.userPoolClient],
    );

    // ── MCP Servers ──────────────────────────────────────────────────────────
    // atlasShaclMcp first: it has no peer dependencies, and atlasSparqlMcp
    // needs its ARN for the construct_and_validate operation.

    this.atlasShaclMcp = new agentcore.Runtime(this, "AtlasShaclMcp", {
      runtimeName: "atlas_shacl_mcp",
      description: "SHACL shape validation against the ATLAS ontology",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("mcp-servers/atlas-shacl-mcp"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
      environmentVariables: {
        SHAPES_S3_URI: "s3://atlas-workshop-1/ontology/atlas-shapes.ttl",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-shacl-mcp" },
    });

    this.atlasSparqlMcp = new agentcore.Runtime(this, "AtlasSparqlMcp", {
      runtimeName: "atlas_sparql_mcp",
      description: "SPARQL query execution against Neptune SLGD/LGD and Ontop",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("mcp-servers/atlas-sparql-mcp"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
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
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("mcp-servers/atlas-er-mcp"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
      environmentVariables: {
        ER_WORKFLOW_NAME: "atlas-entity-resolution",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-er-mcp" },
    });

    this.atlasFiboMcp = new agentcore.Runtime(this, "AtlasFiboMcp", {
      runtimeName: "atlas_fibo_mcp",
      description: "FIBO class and property lookup via atlas-sparql-mcp",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("mcp-servers/atlas-fibo-mcp"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
      environmentVariables: {
        SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-fibo-mcp" },
    });

    this.atlasRegistryMcp = new agentcore.Runtime(this, "AtlasRegistryMcp", {
      runtimeName: "atlas_registry_mcp",
      description: "Agent Registry discovery and capability listing",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("mcp-servers/atlas-registry-mcp"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
      environmentVariables: {
        REGISTRY_ENDPOINT: props.registryEndpoint ?? "",
      },
      tags: { Workshop: "atlas-workshop-2", Component: "atlas-registry-mcp" },
    });

    // ── Agents ───────────────────────────────────────────────────────────────

    this.nlToSparqlAgent = new agentcore.Runtime(this, "NlToSparqlAgent", {
      runtimeName: "nl_to_sparql_agent",
      description: "Translates natural-language questions into validated SPARQL",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("agents/nl-to-sparql-agent"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
      environmentVariables: {
        GROUND_TRUTH_S3_URI: "s3://atlas-workshop-1/prompts/ground-truth.yaml",
        PREFIXES_S3_URI: "s3://atlas-workshop-1/prompts/prefixes.txt",
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
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: componentPath("agents/wealth-signal-detector"),
          runtime: PYTHON_3_12,
          entrypoint: ENTRYPOINT,
        }),
        authorizerConfiguration: authConfig,
        environmentVariables: {
          SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
          SHACL_MCP_ARN: this.atlasShaclMcp.agentRuntimeArn,
          SIGNAL_QUERIES_S3_URI: "s3://atlas-workshop-1/queries/wealth-signals.yaml",
        },
        tags: { Workshop: "atlas-workshop-2", Component: "wealth-signal-detector" },
      },
    );

    this.householdTraverser = new agentcore.Runtime(this, "HouseholdTraverser", {
      runtimeName: "household_traverser",
      description: "Traverses household membership and relationship graphs",
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("agents/household-traverser"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
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
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: componentPath("agents/referral-rationale-drafter"),
          runtime: PYTHON_3_12,
          entrypoint: ENTRYPOINT,
        }),
        authorizerConfiguration: authConfig,
        environmentVariables: {
          SPARQL_MCP_ARN: this.atlasSparqlMcp.agentRuntimeArn,
          BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6",
          PROMPT_TEMPLATE_S3_URI:
            "s3://atlas-workshop-1/prompts/referral-rationale.txt",
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
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: componentPath("agents/behavioral-signal-agent"),
          runtime: PYTHON_3_12,
          entrypoint: ENTRYPOINT,
        }),
        authorizerConfiguration: authConfig,
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
      agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
        path: componentPath("agents/theme-summarizer"),
        runtime: PYTHON_3_12,
        entrypoint: ENTRYPOINT,
      }),
      authorizerConfiguration: authConfig,
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
        agentRuntimeArtifact: agentcore.AgentRuntimeArtifact.fromCodeAsset({
          path: componentPath("agents/conversational-context-manager"),
          runtime: PYTHON_3_12,
          entrypoint: ENTRYPOINT,
        }),
        authorizerConfiguration: authConfig,
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

    // conversational-context-manager is the only Runtime with Memory access
    props.memory.memory.grantFullAccess(this.conversationalContextManager);
  }
}
