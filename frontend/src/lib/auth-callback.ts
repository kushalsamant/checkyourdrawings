export const TOKEN_STORAGE_KEY = "kvshvl_platform_jwt";

export function readOAuthError(): string | null {
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

export function readHandoffCodeFromQuery(): string | null {
  const url = new URL(window.location.href);
  return url.searchParams.get("handoff_code");
}

export async function completeAuthCallback(
  authUrl: string,
): Promise<string | null> {
  const oauthError = readOAuthError();
  if (oauthError) {
    return oauthError;
  }

  const handoffCode = readHandoffCodeFromQuery();
  if (!handoffCode) {
    return "Could not complete sign-in. Try again from the app.";
  }

  const response = await fetch(`${authUrl}/api/handoff/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: handoffCode }),
  });

  if (!response.ok) {
    return "Could not complete sign-in. Try again from the app.";
  }

  const data = (await response.json()) as { access_token?: string };
  if (!data.access_token) {
    return "Could not complete sign-in. Try again from the app.";
  }

  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
  } catch {
    // ignore
  }

  window.location.replace("/");
  return null;
}
