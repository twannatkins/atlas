/**
 * PKCE (Proof Key for Code Exchange) helpers for the Cognito OAuth code flow.
 *
 * The ATLAS app client is a public SPA (generateSecret:false), so the
 * authorization-code flow MUST use PKCE — there is no client secret to
 * authenticate the token exchange. signIn() generates a high-entropy
 * code_verifier, derives the S256 code_challenge, and sends the challenge on
 * the /oauth2/authorize redirect; the /callback handler sends the original
 * verifier to /oauth2/token. Cognito rejects a code exchange whose verifier
 * doesn't hash to the challenge it saw — this binds the redirect to the
 * exchange and defeats authorization-code interception.
 *
 * Browser-only (uses window.crypto.subtle). The verifier is held in
 * sessionStorage across the redirect (cleared after exchange).
 */

const VERIFIER_KEY = "atlas_pkce_verifier";

function base64UrlEncode(bytes: Uint8Array): string {
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Generate a 64-char random PKCE code_verifier and persist it across the redirect. */
export function createAndStoreVerifier(): string {
  const random = new Uint8Array(48);
  window.crypto.getRandomValues(random);
  const verifier = base64UrlEncode(random);
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  return verifier;
}

/** Read (and clear) the stored verifier on the /callback side. */
export function consumeVerifier(): string | null {
  const v = sessionStorage.getItem(VERIFIER_KEY);
  if (v) sessionStorage.removeItem(VERIFIER_KEY);
  return v;
}

/** Derive the S256 code_challenge for a verifier. */
export async function deriveChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier);
  const digest = await window.crypto.subtle.digest("SHA-256", data);
  return base64UrlEncode(new Uint8Array(digest));
}
