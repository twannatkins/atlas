/**
 * GraphQL mutations for the Wholesale UI.
 *
 * Mutations invoke agents through the registry's audit path.
 * Every mutation requires the human-in-the-loop pattern to have
 * been satisfied before it can be called.
 */

import { gql } from "@apollo/client";

/**
 * Route a referral to an advisor.
 *
 * Requires `approvedRationale` — the human must have reviewed and
 * approved the drafted rationale before this mutation can be called.
 * This is the human-in-the-loop gate that makes the workflow compliant.
 */
export const ROUTE_REFERRAL_MUTATION = gql`
  mutation RouteReferral(
    $householdUri: ID!
    $signalUris: [ID!]!
    $approvedRationale: String!
    $originatingBankerId: String!
  ) {
    routeReferral(
      householdUri: $householdUri
      signalUris: $signalUris
      approvedRationale: $approvedRationale
      originatingBankerId: $originatingBankerId
    ) {
      uri
      routingDecision {
        uri
        selectedRoute
        targetAdvisorLabel
      }
      provenance {
        generatedBy
        generatedAtTime
      }
    }
  }
`;

/**
 * Workshop Reset — remove the demo-created advisory relationships + routing decisions,
 * returning the graph to its default seed state so the Rachel→Marcus walkthrough can be
 * re-run cleanly. Seed coverage is never touched.
 */
export const RESET_DEMO_ROUTINGS_MUTATION = gql`
  mutation ResetDemoRoutings {
    resetDemoRoutings {
      status
      advisoryRelationshipsRemoved
      routingDecisionsRemoved
      message
    }
  }
`;


/**
 * Draft a referral rationale from a household's REAL signals (#3).
 *
 * Invokes referral-rationale-drafter (Bedrock). The draft is probabilistic and
 * requires human review — it is NOT a routing action. The banker reviews/edits it,
 * then ROUTE_REFERRAL_MUTATION (the deterministic, human-gated path) does the routing.
 */
export const DRAFT_RATIONALE_MUTATION = gql`
  mutation DraftRationale($householdUri: ID!, $signalUris: [ID!]!) {
    draftRationale(householdUri: $householdUri, signalUris: $signalUris) {
      status
      draftNarrative
      isProbabilistic
      requiresHumanReview
      generatedBy
    }
  }
`;
