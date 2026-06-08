/**
 * OAuth callback view (Wealth UI).
 *
 * Cognito's hosted UI redirects here with ?code=<authorization_code> after a
 * successful login. We exchange the code for tokens via PKCE
 * (exchangeCodeForToken in shared/auth), which persists the access token under
 * "atlas_access_token" — the key the Apollo auth link reads — then redirect to
 * the home page where the session is restored from localStorage.
 *
 * On error (missing code, exchange failure) we show the message rather than
 * silently landing unauthenticated, so a reviewer can see what went wrong.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeCodeForToken } from "../../../../shared/auth/use-auth";

export default function CallbackView() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    const oauthError = params.get("error");

    if (oauthError) {
      setError(`Cognito returned an error: ${oauthError}`);
      return;
    }
    if (!code) {
      setError("No authorization code in the callback URL.");
      return;
    }

    exchangeCodeForToken(code)
      .then(() => {
        router.replace("/");
      })
      .catch((err: Error) => setError(err.message));
  }, [params, router]);

  return (
    <div className="signin-wrap">
      {error ? (
        <div className="signin-card" role="alert">
          <h1>Sign-in failed</h1>
          <p>{error}</p>
          <a className="btn accent" href="/">
            Return home
          </a>
        </div>
      ) : (
        <p className="loading-line" aria-busy="true">
          Completing sign-in…
        </p>
      )}
    </div>
  );
}
