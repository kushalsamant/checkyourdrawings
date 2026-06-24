import { getAuthAccessToken } from "../lib/auth-provider";

const PLATFORM_API_URL = (import.meta.env.VITE_PLATFORM_API_URL ?? "").replace(/\/$/, "");

export interface AccountDetails {
  signed_in: boolean;
  email: string;
  name: string | null;
  paid: boolean;
  subscription_tier: string | null;
  subscription_status: string | null;
  subscription_expires_at: string | null;
  subscription_auto_renew: boolean | null;
  has_subscription: boolean;
}

export async function fetchAccountDetails(): Promise<AccountDetails> {
  if (!PLATFORM_API_URL) {
    throw new Error("Account service is not configured for this environment.");
  }

  const token = getAuthAccessToken();
  if (!token) {
    throw new Error("Sign in to view your account.");
  }

  const response = await fetch(`${PLATFORM_API_URL}/account`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(detail.detail ?? "Could not load account.");
  }

  return (await response.json()) as AccountDetails;
}

export async function cancelSubscription(): Promise<void> {
  if (!PLATFORM_API_URL) {
    throw new Error("Account service is not configured for this environment.");
  }

  const token = getAuthAccessToken();
  if (!token) {
    throw new Error("Sign in to manage your subscription.");
  }

  const response = await fetch(`${PLATFORM_API_URL}/payments/subscriptions/cancel`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(detail.detail ?? "Could not cancel subscription.");
  }
}
