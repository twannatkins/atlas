/**
 * GraphQL queries for the Wholesale UI.
 *
 * Each query uses the fragments defined in fragments.ts.
 * The persona claim is passed via the Apollo Client auth link header,
 * not as a query variable — resolvers read it from the request context.
 */

import { gql } from "@apollo/client";
import {
  CUSTOMER_FIELDS,
  WEALTH_SIGNAL_FIELDS,
  ACCOUNT_FIELDS,
  ADVISORY_RELATIONSHIP_FIELDS,
  REFERRAL_FIELDS,
} from "./fragments";

/** Dashboard query — the banker's assigned book sorted by signal strength */
export const DASHBOARD_QUERY = gql`
  ${CUSTOMER_FIELDS}
  ${WEALTH_SIGNAL_FIELDS}
  query Dashboard($limit: Int) {
    searchCustomers(query: "", limit: $limit) {
      ...CustomerFields
      wealthSignals {
        ...WealthSignalFields
      }
    }
  }
`;

/** Entity 360 — full detail for a single customer */
export const CUSTOMER_360_QUERY = gql`
  ${CUSTOMER_FIELDS}
  ${WEALTH_SIGNAL_FIELDS}
  ${ACCOUNT_FIELDS}
  ${ADVISORY_RELATIONSHIP_FIELDS}
  query Customer360($uri: ID!) {
    customer(uri: $uri) {
      ...CustomerFields
      accounts {
        ...AccountFields
        transactions(limit: 10) {
          uri
          transactionDate
          amountUSD
          transactionType
        }
      }
      wealthSignals {
        ...WealthSignalFields
      }
      advisoryRelationships {
        ...AdvisoryRelationshipFields
      }
      household {
        uri
        label
        members {
          uri
          label
        }
      }
    }
  }
`;

/** Referral detail — signals, rationale, routing decision, audit trail */
export const REFERRAL_DETAIL_QUERY = gql`
  ${WEALTH_SIGNAL_FIELDS}
  ${REFERRAL_FIELDS}
  query ReferralDetail($householdUri: ID!) {
    household(uri: $householdUri) {
      uri
      label
      members {
        uri
        label
      }
    }
    wealthSignals(customerUri: $householdUri) {
      ...WealthSignalFields
    }
    referrals(householdUri: $householdUri) {
      ...ReferralFields
    }
  }
`;

/** Capability palette — persona-scoped agent discovery */
export const CAPABILITIES_QUERY = gql`
  query Capabilities($personaClaim: String!) {
    capabilities(personaClaim: $personaClaim) {
      name
      displayName
      displayIcon
      posture
      capabilityTag
      phase
    }
  }
`;
