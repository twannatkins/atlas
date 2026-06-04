/**
 * Authentication hook for ATLAS Workshop 2.
 *
 * Wraps Cognito authentication and exposes the persona claim.
 * The persona claim is the IDC group that determines what the user
 * can see and do across all four permission layers.
 *
 * In production, signIn() redirects to the Cognito Hosted UI and the
 * token is a real JWT issued by Cognito. In the workshop's local
 * development mode, signIn() sets demo credentials in localStorage
 * so the UI can render without a running Cognito pool.
 */

import { useState, useEffect, useCallback } from "react";
import { createAndStoreVerifier, deriveChallenge, consumeVerifier } from "./pkce";

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

/** Whether the app is running in local development mode (no Cognito pool). */
const IS_LOCAL_DEV =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");

/**
 * Hook that provides authentication state and persona claim.
 *
 * In production, this integrates with Cognito Hosted UI via OAuth
 * authorization code flow. The JWT is validated server-side by AppSync;
 * the persona claim is extracted from the token's cognito:groups claim.
 *
 * In local development (localhost), it uses localStorage-backed demo
 * credentials so the UI can render without a running Cognito pool.
 * This path is never reachable in deployed environments because
 * CloudFront serves the app from a non-localhost origin.
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
    if (!IS_LOCAL_DEV) {
      // Production: redirect to the Cognito hosted UI using the OAuth
      // authorization-code flow with PKCE. The app client is a public SPA
      // (no secret), so PKCE is required: we generate a code_verifier, send
      // its S256 challenge here, and the /callback route exchanges the code
      // with the original verifier. The callback handler stores the access
      // token under "atlas_access_token" (the key the Apollo client reads).
      const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
      const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
      const redirectUri = encodeURIComponent(window.location.origin + "/callback");
      const verifier = createAndStoreVerifier();
      const challenge = await deriveChallenge(verifier);
      window.location.href =
        `${cognitoDomain}/oauth2/authorize?response_type=code&client_id=${clientId}` +
        `&redirect_uri=${redirectUri}&scope=openid+profile` +
        `&code_challenge=${challenge}&code_challenge_method=S256`;
      return;
    }

    // Local development only: set demo credentials for UI rendering.
    // This code path is unreachable in deployed environments.
    const persona = "atlas-consumer-banker";
    const user = "rachel-kim";
    const name = "Rachel Kim";

    localStorage.setItem("atlas_persona", persona);
    localStorage.setItem("atlas_user_id", user);
    localStorage.setItem("atlas_display_name", name);
    localStorage.setItem("atlas_token", "local-dev-token");

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

    if (!IS_LOCAL_DEV) {
      // Production: redirect to Cognito logout endpoint
      const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
      const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
      const logoutUri = encodeURIComponent(window.location.origin);
      window.location.href =
        `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${logoutUri}`;
    }
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

/** Decode a JWT payload (no signature check — AppSync verifies server-side). */
function decodeJwtPayload(token: string): Record<string, any> {
  try {
    const part = token.split(".")[1];
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return {};
  }
}

/**
 * Exchange the authorization code for tokens at Cognito's /oauth2/token endpoint
 * (PKCE — sends the stored code_verifier, no client secret). Called by the
 * /callback route. On success it persists the access token under
 * "atlas_access_token" (the key the Apollo auth link reads) and derives the
 * persona/user/display-name from the token claims, then returns the persona.
 *
 * Throws on any failure so the callback page can show an error instead of
 * silently landing unauthenticated.
 */
export async function exchangeCodeForToken(code: string): Promise<{ persona: string }> {
  const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!cognitoDomain || !clientId) {
    throw new Error("Cognito domain/client not configured (NEXT_PUBLIC_COGNITO_DOMAIN / _CLIENT_ID).");
  }

  const verifier = consumeVerifier();
  if (!verifier) {
    throw new Error("Missing PKCE verifier — start sign-in again.");
  }

  const redirectUri = window.location.origin + "/callback";
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: clientId,
    code,
    redirect_uri: redirectUri,
    code_verifier: verifier,
  });

  const resp = await fetch(`${cognitoDomain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  if (!resp.ok) {
    throw new Error(`Token exchange failed (${resp.status}): ${await resp.text()}`);
  }
  const tokens = await resp.json();
  const accessToken: string = tokens.access_token;
  if (!accessToken) {
    throw new Error("Token response missing access_token.");
  }

  // The resolver reads custom:persona then falls back to cognito:groups[0]
  // (sparql_resolver.py:115-119). Mirror that here for the UI's local state.
  const claims = decodeJwtPayload(accessToken);
  const groups: string[] = claims["cognito:groups"] || [];
  const persona = claims["custom:persona"] || groups[0] || "atlas-consumer-banker";
  const user = claims["username"] || claims["sub"] || "";

  // atlas_access_token is the key providers.tsx prefers for the Authorization
  // header; persona/user/display feed the existing session-restore in useAuth.
  localStorage.setItem("atlas_access_token", accessToken);
  localStorage.setItem("atlas_persona", persona);
  localStorage.setItem("atlas_user_id", user);
  localStorage.setItem("atlas_display_name", user);

  return { persona };
}
