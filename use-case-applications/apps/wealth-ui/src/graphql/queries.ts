/**
 * GraphQL queries for the Wealth UI.
 *
 * Same schema as the Wholesale UI but different fragments — the Wealth
 * Advisor cares about coverage, themes, and behavioral signals rather
 * than referral pipeline data.
 */

import { gql } from "@apollo/client";

/**
 * #5 conversation — a single natural-language turn via conversational-context-manager.
 * Single-turn: priorTurns is always 0 (AgentCore Memory is not wired). Returns real rows
 * for a matched template, or status "no_template_match" (the UI then shows suggestions).
 */
export const CONVERSE_MUTATION = gql`
  mutation Converse($question: String!, $sessionId: String!) {
    converse(question: $question, sessionId: $sessionId) {
      status
      sparql
      result
      priorTurns
    }
  }
`;

/**
 * The questions the conversation can actually answer — read live from the same
 * ground-truth.yaml the agent matches against (zero drift; the field is shared with the
 * Wholesale UI). Rendered as suggestions + the no-match state.
 */
export const SUGGESTED_QUESTIONS_QUERY = gql`
  query SuggestedQuestions {
    suggestedQuestions
  }
`;

export const ADVISOR_DASHBOARD_QUERY = gql`
  query AdvisorDashboard($limit: Int) {
    searchCustomers(query: "", limit: $limit) {
      uri
      customerId
      label
      advisoryRelationships {
        uri
        advisor { uri label }
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
