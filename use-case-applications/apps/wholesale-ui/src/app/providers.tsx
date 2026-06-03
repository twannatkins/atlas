"use client";

import { ApolloClient, ApolloProvider, InMemoryCache, createHttpLink } from "@apollo/client";
import { setContext } from "@apollo/client/link/context";

const httpLink = createHttpLink({
  uri: process.env.NEXT_PUBLIC_APPSYNC_ENDPOINT || "http://localhost:4000/graphql",
});

const authLink = setContext((_, { headers }) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("atlas_access_token") || localStorage.getItem("atlas_token") : null;
  return { headers: { ...headers, authorization: token ?? "" } };
});

const apolloClient = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache({
    typePolicies: {
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

export function Providers({ children }: { children: React.ReactNode }) {
  return <ApolloProvider client={apolloClient}>{children}</ApolloProvider>;
}
