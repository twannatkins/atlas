/**
 * GraphQL queries for the Wealth UI.
 *
 * Same schema as the Wholesale UI but different fragments — the Wealth
 * Advisor cares about coverage, themes, and behavioral signals rather
 * than referral pipeline data.
 */

import { gql } from "@apollo/client";

export const ADVISOR_DASHBOARD_QUERY = gql`
  query AdvisorDashboard($limit: Int) {
    searchCustomers(query: "", limit: $limit) {
      uri
      customerId
      label
      advisoryRelationships {
        uri
        advisor { label }
        isActive
        coverageStartDate
      }
    }
  }
`;

export const CLIENT_360_QUERY = gql`
  query Client360($uri: ID!) {
    customer(uri: $uri) {
      uri
      customerId
      label
      advisoryRelationships {
        uri
        advisor { uri label }
        coverageStartDate
        coverageEndDate
        relationshipType
        isActive
      }
      wealthSignals {
        uri
        signalType
        strength
        signalDate
        provenance { validatedBy derivedFrom generatedBy }
      }
      household {
        uri
        label
        members { uri label }
      }
    }
  }
`;

export const THEMES_QUERY = gql`
  query Themes($limit: Int) {
    themes(limit: $limit) {
      uri
      themeLabel
      themeDate
      sourceArticles
    }
  }
`;

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
