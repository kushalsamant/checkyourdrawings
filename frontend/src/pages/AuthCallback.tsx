import { useEffect, useState } from "react";

const TOKEN_STORAGE_KEY = "kvshvl_platform_jwt";

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

function readAccessTokenFromHash(): string | null {
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  if (!hash) {
    return null;
  }
  const params = new URLSearchParams(hash);
  return params.get("access_token");
}

export function AuthCallback() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (callbackStarted) {
      return;
    }
    callbackStarted = true;

    let cancelled = false;

    async function completeSignIn(): Promise<void> {
      const oauthError = readOAuthError();
      if (oauthError) {
        if (!cancelled) {
          setError(oauthError);
        }
        return;
      }

      const accessToken = readAccessTokenFromHash();
      if (accessToken) {
        try {
          sessionStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
        } catch {
          // ignore
        }
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
