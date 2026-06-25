import { clearAuthAccessToken } from "../lib/auth-provider";

const PLATFORM_API_URL = (import.meta.env.VITE_PLATFORM_API_URL ?? "").replace(/\/$/, "");

export const SESSION_EXPIRED_MESSAGE =
  "Your session expired. Sign in again.";

export function isPlatformApiConfigured(): boolean {
  return Boolean(PLATFORM_API_URL);
}

export async function platformApiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  if (!PLATFORM_API_URL) {
    throw new Error("Account service is not configured here.");
  }

  const headers = new Headers(init.headers);
  const response = await fetch(`${PLATFORM_API_URL}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    clearAuthAccessToken();
  }

  return response;
}

export async function readPlatformApiError(
  response: Response,
  fallback: string,
): Promise<string> {
  if (response.status === 401) {
    return SESSION_EXPIRED_MESSAGE;
  }

  const detail = (await response.json().catch(() => ({}))) as { detail?: string };
  return detail.detail ?? fallback;
}
