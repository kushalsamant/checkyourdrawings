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

let callbackStarted = false;

export function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (callbackStarted) {
      return;
    }
    callbackStarted = true;

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

      // detectSessionInUrl exchanges ?code= during getSession().
      const { data, error: sessionError } = await authClient.auth.getSession();
      if (sessionError) {
        if (!cancelled) {
          setError(sessionError.message);
        }
        return;
      }

      if (data.session) {
        window.location.replace("/");
        return;
      }

      if (!cancelled) {
        setError("Could not complete sign-in. Try again from the app.");
      }
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
