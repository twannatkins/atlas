/**
 * Apollo Client configuration for ATLAS Workshop 2.
 *
 * Connects to the AppSync GraphQL endpoint. Authentication is handled
 * via the Cognito JWT — AppSync extracts the persona claim from the
 * token's cognito:groups claim server-side. The client never sends the
 * persona as a separate header; doing so would allow client-side
 * privilege escalation by modifying localStorage.
 */

import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";
import { setContext } from "@apollo/client/link/context";

const GRAPHQL_ENDPOINT =
  process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "http://localhost:4000/graphql";

const httpLink = createHttpLink({
  uri: GRAPHQL_ENDPOINT,
});

/**
 * Auth link that attaches the Cognito JWT to every request.
 *
 * The persona claim is extracted server-side from the JWT's
 * cognito:groups claim by the AppSync resolver. This ensures the
 * persona cannot be spoofed by modifying client-side state.
 */
const authLink = setContext((_, { headers }) => {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("atlas_token")
      : null;

  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
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
