/**
 * Apollo Client configuration for ATLAS Workshop 2.
 *
 * Connects to the AppSync GraphQL endpoint. The persona claim is
 * extracted from the Cognito JWT and passed as a header on every request.
 * Resolvers use this header to scope data via Lake Formation.
 */

import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";
import { setContext } from "@apollo/client/link/context";

const GRAPHQL_ENDPOINT =
  process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "http://localhost:4000/graphql";

const httpLink = createHttpLink({
  uri: GRAPHQL_ENDPOINT,
});

/**
 * Auth link that attaches the Cognito JWT and persona claim to every request.
 * The persona claim is what the MCP servers use for Lake Formation scoping.
 */
const authLink = setContext((_, { headers }) => {
  // In production, this comes from Cognito via useAuth hook
  const token = typeof window !== "undefined" ? localStorage.getItem("atlas_token") : null;
  const personaClaim = typeof window !== "undefined" ? localStorage.getItem("atlas_persona") : null;

  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
      "x-atlas-persona": personaClaim || "",
    },
  };
});

/**
 * Apollo Client instance shared across both UIs.
 *
 * The cache is normalized by URI (every GraphQL type has a `uri: ID!` field)
 * which maps directly to the ontology's URI-based identity model.
 */
export const client = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache({
    typePolicies: {
      // Use `uri` as the cache key for all ATLAS types
      Customer: { keyFields: ["uri"] },
      Account: { keyFields: ["uri"] },
      Household: { keyFields: ["uri"] },
      WealthSignal: { keyFields: ["uri"] },
      AdvisoryRelationship: { keyFields: ["uri"] },
      Advisor: { keyFields: ["uri"] },
      RoutingDecision: { keyFields: ["uri"] },
      AuditRecord: { keyFields: ["uri"] },
      Referral: { keyFields: ["uri"] },
    },
  }),
});
