/**
 * Hook that queries the Agent Registry for persona-scoped capabilities.
 *
 * Wealth Advisor persona sees: theme-summarizer, conversational-context-manager,
 * behavioral-signal-agent. Same hook pattern as Wholesale UI — registry-first discovery.
 */

import { useQuery } from "@apollo/client";
import { CAPABILITIES_QUERY } from "../graphql/queries";

export interface Capability {
  name: string;
  displayName: string;
  displayIcon: string;
  posture: string;
  capabilityTag: string;
  phase: number;
}

interface UseCapabilitiesResult {
  capabilities: Capability[];
  loading: boolean;
  error: Error | undefined;
}

export function useCapabilities(personaClaim: string): UseCapabilitiesResult {
  const { data, loading, error } = useQuery(CAPABILITIES_QUERY, {
    variables: { personaClaim },
    skip: !personaClaim,
  });

  return {
    capabilities: data?.capabilities ?? [],
    loading,
    error: error as Error | undefined,
  };
}
