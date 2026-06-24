import { useEffect, useState } from "react";

import { completeAuthCallback, readOAuthError } from "../lib/auth-callback";

const AUTH_URL = (import.meta.env.VITE_KVSHVL_AUTH_URL ?? "").replace(/\/$/, "");

export function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function run() {
      const oauthError = readOAuthError();
      if (oauthError) {
        setError(oauthError);
        return;
      }

      if (!AUTH_URL) {
        setError("VITE_KVSHVL_AUTH_URL is not configured for this environment.");
        return;
      }

      const callbackError = await completeAuthCallback(AUTH_URL);
      if (callbackError) {
        setError(callbackError);
      }
    }

    void run();
  }, []);

  if (!error) {
    return (
      <div className="page-body">
        <main className="app-shell auth-callback">
          <p>Completing sign-in…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="page-body">
      <main className="app-shell auth-callback">
        <p role="alert">{error}</p>
        <p>
          <a href="/">Back to app</a>
        </p>
      </main>
    </div>
  );
}
