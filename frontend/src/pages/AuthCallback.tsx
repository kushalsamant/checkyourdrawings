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

      // AuthProvider may have already exchanged ?code= via detectSessionInUrl.
      const { data: existingSession, error: sessionError } =
        await authClient.auth.getSession();
      if (sessionError) {
        if (!cancelled) {
          setError(sessionError.message);
        }
        return;
      }

      if (existingSession.session) {
        window.location.replace("/");
        return;
      }

      const code = new URL(window.location.href).searchParams.get("code");
      if (code) {
        const { error: exchangeError } =
          await authClient.auth.exchangeCodeForSession(code);
        if (exchangeError) {
          if (!cancelled) {
            setError(exchangeError.message);
          }
          return;
        }

        window.location.replace("/");
        return;
      }

      // Implicit/hash callback — getSession triggers detectSessionInUrl again.
      const { data: detectedSession, error: detectError } =
        await authClient.auth.getSession();
      if (detectError) {
        if (!cancelled) {
          setError(detectError.message);
        }
        return;
      }

      if (detectedSession.session) {
        window.location.replace("/");
        return;
      }

      if (!cancelled) {
        setError("Could not complete sign-in. Try again from the app.");
      }
    }

    const {
      data: { subscription },
    } = authClient.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_IN" && session) {
        window.location.replace("/");
      }
    });

    void completeSignIn();

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  return (
    <main className="app-shell">
      <p>{error ?? "Completing sign-in..."}</p>
    </main>
  );
}
