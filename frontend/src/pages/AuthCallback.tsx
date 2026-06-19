import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "";

export function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) {
      setError("Supabase is not configured.");
      return;
    }

    const supabase = createClient(supabaseUrl, supabaseAnonKey);
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");

    if (!code) {
      setError("Missing OAuth code in callback URL.");
      return;
    }

    supabase.auth
      .exchangeCodeForSession(code)
      .then(({ error: exchangeError }) => {
        if (exchangeError) {
          setError(exchangeError.message);
          return;
        }
        window.location.replace("/");
      })
      .catch((callbackError: unknown) => {
        setError(
          callbackError instanceof Error
            ? callbackError.message
            : "Failed to complete sign-in.",
        );
      });
  }, []);

  return (
    <main className="app-shell">
      <p>{error ?? "Completing sign-in..."}</p>
    </main>
  );
}
