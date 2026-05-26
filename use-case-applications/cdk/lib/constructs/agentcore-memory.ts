/**
 * AgentCore Memory store — single per-stack store for conversational context.
 *
 * Stores multi-turn conversation context for stateful agents. Currently
 * only `conversational-context-manager` writes to this store (via the
 * AgentCore Memory API: GetMemory/PutMemory/DeleteMemory). Other agents
 * are stateless and do not access Memory.
 *
 * Architectural commitment from spec/11-identity-and-session.md:
 *   - One Memory store per stack (this construct creates it).
 *   - Sessions partitioned by Cognito sub + session_id, supplied by the UI.
 *   - Per-user isolation enforced at the AgentCore Identity layer above.
 *
 * Why L2 (Memory) and not L1 (CfnMemory): the L2 class provides grant
 * helpers (grantFullAccess, grantRead, grantWrite, grantDelete) that
 * map cleanly to the IAM permissions in the agent descriptor. Using L1
 * would mean writing those IAM statements by hand.
 *
 * Why no memoryStrategies: ATLAS uses short-term (raw event) memory
 * only. Long-term memory strategies (semantic, summary, user-preference)
 * would add value for production agents that need to recall context
 * across sessions, but the workshop's pedagogical scope stops at
 * within-session multi-turn context.
 *
 * Why removalPolicy DESTROY: workshop teardown should clean up cleanly.
 * Production deployments should override this to RETAIN.
 */

import * as cdk from "aws-cdk-lib";
import * as agentcore from "aws-cdk-lib/aws-bedrockagentcore";
import { Construct } from "constructs";

export interface AgentCoreMemoryProps {
  /**
   * Override the default memory name. Must match the AgentCore naming
   * constraint: [a-zA-Z][a-zA-Z0-9_]{0,47} (underscores allowed, no hyphens).
   * @default "atlas_workshop_memory"
   */
  readonly memoryName?: string;

  /**
   * Override the default expiration duration. The L2 Memory default is
   * 90 days. ATLAS uses the default for workshop sessions; production
   * deployments may want a shorter window.
   * @default cdk.Duration.days(90)
   */
  readonly expirationDuration?: cdk.Duration;
}

export class AgentCoreMemoryConstruct extends Construct {
  public readonly memory: agentcore.Memory;
  public readonly memoryArn: string;
  public readonly memoryId: string;

  constructor(scope: Construct, id: string, props?: AgentCoreMemoryProps) {
    super(scope, id);

    this.memory = new agentcore.Memory(this, "Memory", {
      memoryName: props?.memoryName ?? "atlas_workshop_memory",
      description: "ATLAS Workshop 2 multi-turn conversation context store - see spec docs for session model",
      expirationDuration: props?.expirationDuration,
      // No custom kmsKey — uses AWS-managed encryption.
      // No custom executionRole — L2 creates one as needed.
      // No memoryStrategies — short-term raw-event memory only;
      //   no long-term extraction is needed for the workshop's scope.
      tags: {
        Workshop: "atlas-workshop-2",
        Component: "agentcore-memory",
      },
    });

    // Apply removal policy: workshop teardown should clean up cleanly.
    // Production deployments override to RETAIN before deploy.
    this.memory.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);

    this.memoryArn = this.memory.memoryArn;
    this.memoryId = this.memory.memoryId;
  }
}
