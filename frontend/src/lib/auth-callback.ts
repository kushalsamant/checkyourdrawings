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

export function readAccessTokenFromHash(): string | null {
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  if (!hash) {
    return null;
  }

  const params = new URLSearchParams(hash);
  return params.get("access_token");
}

export function tryCompleteAuthCallback(): string | null {
  const oauthError = readOAuthError();
  if (oauthError) {
    return oauthError;
  }

  const accessToken = readAccessTokenFromHash();
  if (!accessToken) {
    return "Could not complete sign-in. Try again from the app.";
  }

  try {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
  } catch {
    // ignore
  }

  window.location.replace("/");
  return null;
}
