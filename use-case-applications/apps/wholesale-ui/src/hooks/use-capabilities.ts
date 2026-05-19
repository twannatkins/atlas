/**
 * Hook that queries the Agent Registry for persona-scoped capabilities.
 *
 * This is the second driver in the two-driver architecture: the registry
 * tells the UI what actions to render. When a new agent is registered,
 * this hook returns it automatically — no UI redeploy needed.
 *
 * This is Thesis 1: registry-first agent discovery.
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
