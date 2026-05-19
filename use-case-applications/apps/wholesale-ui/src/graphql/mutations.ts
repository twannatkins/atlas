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
      }
      provenance {
        generatedBy
        generatedAtTime
      }
    }
  }
`;

/**
 * Detect wealth signals for a target customer or household.
 *
 * This is a deterministic operation — same input produces same signals.
 * No human-in-the-loop required because the output is evidence, not a decision.
 */
export const DETECT_SIGNALS_MUTATION = gql`
  mutation DetectSignals($targetUri: ID!, $signalTypes: [String!]) {
    detectSignals(targetUri: $targetUri, signalTypes: $signalTypes) {
      uri
      signalType
      strength
      signalDate
      provenance {
        validatedBy
        derivedFrom
        generatedBy
      }
    }
  }
`;
