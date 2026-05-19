/**
 * Hook that fetches wealth signals for a customer.
 *
 * Signals are graph-native data (Pattern 2: Direct Neptune SPARQL).
 * Each signal carries provenance showing which SHACL shape validated it
 * and which R2RML mapping produced the underlying triple.
 */

import { useQuery } from "@apollo/client";
import { gql } from "@apollo/client";
import { WEALTH_SIGNAL_FIELDS } from "../graphql/fragments";

const SIGNALS_QUERY = gql`
  ${WEALTH_SIGNAL_FIELDS}
  query WealthSignals($customerUri: ID!) {
    wealthSignals(customerUri: $customerUri) {
      ...WealthSignalFields
    }
  }
`;

export function useSignals(customerUri: string) {
  const { data, loading, error } = useQuery(SIGNALS_QUERY, {
    variables: { customerUri },
    skip: !customerUri,
  });

  return {
    signals: data?.wealthSignals ?? [],
    loading,
    error: error as Error | undefined,
  };
}
