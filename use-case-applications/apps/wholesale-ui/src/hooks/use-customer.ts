/**
 * Hook that fetches a customer's full Entity 360 data.
 *
 * The query is scoped by the persona claim passed in the auth header.
 * A Consumer Banker sees their assigned book; a BSA Analyst sees all.
 * The hook doesn't know about scoping — it trusts the resolver + MCP layer.
 */

import { useQuery } from "@apollo/client";
import { CUSTOMER_360_QUERY } from "../graphql/queries";

export function useCustomer(uri: string) {
  const { data, loading, error } = useQuery(CUSTOMER_360_QUERY, {
    variables: { uri },
    skip: !uri,
  });

  return {
    customer: data?.customer ?? null,
    loading,
    error: error as Error | undefined,
  };
}
