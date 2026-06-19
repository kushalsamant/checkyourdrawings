import { useEffect, useState } from "react";

import { getSupabaseClient } from "../lib/supabase";

function readOAuthError(): string | null {
  const url = new URL(window.location.href);
  const fromQuery =
    url.searchParams.get("error_description") ?? url.searchParams.get("error");
  if (fromQuery) {
    return fromQuery;
  }

  const hash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
  if (!hash) {
    return null;
  }

  const hashParams = new URLSearchParams(hash);
  return hashParams.get("error_description") ?? hashParams.get("error");
}

function sessionStorageKey(code: string): string {
  return `cyd_oauth_exchange_${code}`;
}

let inflightExchange: Promise<{ error: { message: string } | null }> | null =
  null;

export function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (supabase === null) {
      setError("Supabase is not configured.");
      return;
    }

    const authClient = supabase;
    let cancelled = false;

    async function completeSignIn(): Promise<void> {
      const oauthError = readOAuthError();
      if (oauthError) {
        if (!cancelled) {
          setError(oauthError);
        }
        return;
      }

      const code = new URL(window.location.href).searchParams.get("code");
      if (!code) {
        if (!cancelled) {
          setError("Could not complete sign-in. Try again from the app.");
        }
        return;
      }

      const storageKey = sessionStorageKey(code);

      const { data: existingSession } = await authClient.auth.getSession();
      if (existingSession.session) {
        window.location.replace("/");
        return;
      }

      if (sessionStorage.getItem(storageKey) === "done") {
        const { data: storedSession } = await authClient.auth.getSession();
        if (storedSession.session) {
          window.location.replace("/");
          return;
        }
      }

      if (inflightExchange === null) {
        inflightExchange = authClient.auth
          .exchangeCodeForSession(code)
          .then((result) => {
            if (!result.error) {
              sessionStorage.setItem(storageKey, "done");
            }
            return { error: result.error };
          })
          .finally(() => {
            inflightExchange = null;
          });
      }

      const { error: exchangeError } = await inflightExchange;
      if (exchangeError) {
        if (!cancelled) {
          setError(exchangeError.message);
        }
        return;
      }

      window.location.replace("/");
    }

    void completeSignIn();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="app-shell">
      <p>{error ?? "Completing sign-in..."}</p>
    </main>
  );
}
