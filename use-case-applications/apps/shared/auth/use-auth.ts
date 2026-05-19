/**
 * Authentication hook for ATLAS Workshop 2.
 *
 * Wraps Cognito authentication and exposes the persona claim.
 * The persona claim is the IDC group that determines what the user
 * can see and do across all four permission layers.
 */

import { useState, useEffect, useCallback } from "react";

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  personaClaim: string;
  userId: string;
  displayName: string;
  signIn: () => Promise<void>;
  signOut: () => void;
}

/**
 * Valid persona claims in ATLAS. Each maps to an IDC group.
 * The persona determines:
 *   - Which capability palette the UI renders (Registry layer)
 *   - Which routes are accessible (Application layer / Cognito)
 *   - Which data rows are returned (Data layer / Lake Formation)
 *   - Which named graphs are traversable (Semantic layer / SHACL)
 */
export const VALID_PERSONAS = [
  "atlas-consumer-banker",
  "atlas-wealth-advisor",
  "atlas-bsa-analyst",
  "atlas-ontology-steward",
  "atlas-auditor",
] as const;

export type PersonaClaim = (typeof VALID_PERSONAS)[number];

/**
 * Hook that provides authentication state and persona claim.
 *
 * In production, this integrates with Cognito Hosted UI.
 * In the workshop, it reads from localStorage for demo purposes.
 */
export function useAuth(): AuthState {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [personaClaim, setPersonaClaim] = useState("");
  const [userId, setUserId] = useState("");
  const [displayName, setDisplayName] = useState("");

  useEffect(() => {
    // Check for existing session
    const storedPersona = localStorage.getItem("atlas_persona");
    const storedUser = localStorage.getItem("atlas_user_id");
    const storedName = localStorage.getItem("atlas_display_name");

    if (storedPersona && storedUser) {
      setPersonaClaim(storedPersona);
      setUserId(storedUser);
      setDisplayName(storedName || "");
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const signIn = useCallback(async () => {
    // In production: redirect to Cognito Hosted UI
    // In workshop: set demo credentials
    const persona = "atlas-consumer-banker";
    const user = "rachel-kim";
    const name = "Rachel Kim";

    localStorage.setItem("atlas_persona", persona);
    localStorage.setItem("atlas_user_id", user);
    localStorage.setItem("atlas_display_name", name);
    localStorage.setItem("atlas_token", "demo-token");

    setPersonaClaim(persona);
    setUserId(user);
    setDisplayName(name);
    setIsAuthenticated(true);
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem("atlas_persona");
    localStorage.removeItem("atlas_user_id");
    localStorage.removeItem("atlas_display_name");
    localStorage.removeItem("atlas_token");

    setPersonaClaim("");
    setUserId("");
    setDisplayName("");
    setIsAuthenticated(false);
  }, []);

  return {
    isAuthenticated,
    isLoading,
    personaClaim,
    userId,
    displayName,
    signIn,
    signOut,
  };
}
