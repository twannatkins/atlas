/**
 * Step Functions state machine for the referral-orchestrator workflow.
 *
 * Five steps, each invoking a dedicated Lambda:
 *   select-advisor → validate-routing → write-routing-decision → notify-advisor → audit-write
 *
 * Why Step Functions: auditability. Every state transition is recorded.
 * The execution ARN is the answer to "what happened to referral X?"
 */

import * as cdk from "aws-cdk-lib";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as tasks from "aws-cdk-lib/aws-stepfunctions-tasks";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

export interface StepFunctionsProps {
  selectAdvisorFn: lambda.Function;
  validateRoutingFn: lambda.Function;
  writeRoutingDecisionFn: lambda.Function;
  notifyAdvisorFn: lambda.Function;
  auditWriteFn: lambda.Function;
}

export class StepFunctionsConstruct extends Construct {
  public readonly stateMachineArn: string;

  constructor(scope: Construct, id: string, props: StepFunctionsProps) {
    super(scope, id);

    // Step 1: Select advisor — queries SLGD for eligible advisors
    const selectAdvisor = new tasks.LambdaInvoke(this, "SelectAdvisor", {
      lambdaFunction: props.selectAdvisorFn,
      outputPath: "$.Payload",
      retryOnServiceExceptions: true,
    });

    // Step 2: Validate routing — SHACL validation of routing decision
    const validateRouting = new tasks.LambdaInvoke(this, "ValidateRouting", {
      lambdaFunction: props.validateRoutingFn,
      outputPath: "$.Payload",
      // No retry on validation failure — surface to human
    });

    // Step 3: Write routing decision — INSERT to SLGD with PROV-O
    const writeDecision = new tasks.LambdaInvoke(this, "WriteRoutingDecision", {
      lambdaFunction: props.writeRoutingDecisionFn,
      outputPath: "$.Payload",
      retryOnServiceExceptions: true,
    });

    // Step 4: Notify advisor — CloudWatch event (non-fatal on failure)
    const notifyAdvisor = new tasks.LambdaInvoke(this, "NotifyAdvisor", {
      lambdaFunction: props.notifyAdvisorFn,
      outputPath: "$.Payload",
      retryOnServiceExceptions: true,
    });

    // Step 5: Audit write — must succeed (compensating transaction)
    const auditWrite = new tasks.LambdaInvoke(this, "AuditWrite", {
      lambdaFunction: props.auditWriteFn,
      outputPath: "$.Payload",
      retryOnServiceExceptions: true,
    });

    // Failure state
    const failed = new sfn.Fail(this, "ReferralFailed", {
      cause: "Routing validation failed or no eligible advisor",
      error: "REFERRAL_ROUTING_FAILED",
    });

    // Chain: linear sequence with validation gate
    const definition = selectAdvisor
      .next(
        new sfn.Choice(this, "AdvisorFound?")
          .when(
            sfn.Condition.stringEquals("$.status", "no_eligible_advisor"),
            failed,
          )
          .otherwise(validateRouting),
      );

    validateRouting.next(
      new sfn.Choice(this, "ValidationPassed?")
        .when(
          sfn.Condition.stringEquals("$.status", "validation_failed"),
          failed,
        )
        .otherwise(writeDecision.next(notifyAdvisor).next(auditWrite)),
    );

    const stateMachine = new sfn.StateMachine(this, "ReferralOrchestrator", {
      stateMachineName: "atlas-referral-orchestrator",
      definitionBody: sfn.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(5),
      tracingEnabled: true,
    });

    this.stateMachineArn = stateMachine.stateMachineArn;
  }
}
