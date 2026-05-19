/**
 * GraphQL fragments for the Wholesale UI.
 *
 * Every fragment maps to a FIBO-aligned type in the schema.
 * The fragment names match the ontology class names so a developer
 * who knows the ontology can navigate the code without documentation.
 */

import { gql } from "@apollo/client";

/** atlas:Customer — the primary entity in the Wholesale UI */
export const CUSTOMER_FIELDS = gql`
  fragment CustomerFields on Customer {
    uri
    customerId
    label
    household {
      uri
      label
      memberCount
    }
  }
`;

/** atlas:WealthSignal — signals with provenance for audit trail */
export const WEALTH_SIGNAL_FIELDS = gql`
  fragment WealthSignalFields on WealthSignal {
    uri
    signalType
    strength
    signalDate
    provenance {
      validatedBy
      derivedFrom
      generatedBy
      generatedAtTime
    }
  }
`;

/** atlas:Account — financial accounts held by a customer */
export const ACCOUNT_FIELDS = gql`
  fragment AccountFields on Account {
    uri
    accountId
    accountType
    balanceUSD
  }
`;

/** atlas:AdvisoryRelationship — coverage assignments */
export const ADVISORY_RELATIONSHIP_FIELDS = gql`
  fragment AdvisoryRelationshipFields on AdvisoryRelationship {
    uri
    advisor {
      uri
      label
    }
    coverageStartDate
    coverageEndDate
    relationshipType
    isActive
  }
`;

/** atlas-part-2:Referral — the business-facing referral noun */
export const REFERRAL_FIELDS = gql`
  fragment ReferralFields on Referral {
    uri
    approvedRationale
    referralDate
    originatedBy
    routingDecision {
      uri
      selectedRoute
      humanReview {
        reviewOutcome
        reviewDate
      }
    }
    provenance {
      generatedBy
      generatedAtTime
    }
  }
`;
