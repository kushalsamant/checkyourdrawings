import { getAuthAccessToken } from "../lib/auth-provider";
import {
  isPlatformApiConfigured,
  platformApiFetch,
  readPlatformApiError,
} from "./platform-api";

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
  if (!isPlatformApiConfigured()) {
    throw new Error("Account service is not configured for this environment.");
  }

  const token = getAuthAccessToken();
  if (!token) {
    throw new Error("Sign in to view your account.");
  }

  const response = await platformApiFetch("/account", {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(await readPlatformApiError(response, "Could not load account."));
  }

  return (await response.json()) as AccountDetails;
}

export async function cancelSubscription(): Promise<void> {
  if (!isPlatformApiConfigured()) {
    throw new Error("Account service is not configured for this environment.");
  }

  const token = getAuthAccessToken();
  if (!token) {
    throw new Error("Sign in to manage your subscription.");
  }

  const response = await platformApiFetch("/payments/subscriptions/cancel", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    throw new Error(await readPlatformApiError(response, "Could not cancel subscription."));
  }
}
