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
      advisoryRelationships {
        uri
        isActive
        advisor {
          label
        }
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

/**
 * Ask the graph (#2) — natural-language query via nl-to-sparql-agent.
 * Template-bounded: returns real rows for a matched template, or status
 * "no_template_match" (the UI then shows SUGGESTED_QUESTIONS — never a fabricated answer).
 */
export const ASK_GRAPH_QUERY = gql`
  query AskGraph($question: String!) {
    askGraph(question: $question) {
      status
      sparql
      result
      templateId
      executionTimeMs
    }
  }
`;

/**
 * The questions Ask-the-graph can actually answer — read live from the same
 * ground-truth.yaml the agent matches against (zero drift). Rendered as suggestions
 * and as the no-match state, so the input is never a bare "ask anything" box.
 */
export const SUGGESTED_QUESTIONS_QUERY = gql`
  query SuggestedQuestions {
    suggestedQuestions
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
