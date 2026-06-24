const PLATFORM_API_URL = (import.meta.env.VITE_PLATFORM_API_URL ?? "").replace(/\/$/, "");

export interface PricingTier {
  tier: string;
  amount: number;
  currency: string;
  payment_type: string;
}

export interface CheckoutSession {
  key_id: string;
  payment_type: string;
  tier: string;
  subscription_id?: string | null;
  amount?: number | null;
  currency: string;
  description: string;
  prefill: { email: string; name: string };
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

export async function fetchPricingTiers(): Promise<PricingTier[]> {
  if (!PLATFORM_API_URL) {
    return [];
  }
  const response = await fetch(`${PLATFORM_API_URL}/payments/plans?app=checkyourdrawings`);
  if (!response.ok) {
    return [];
  }
  const data = (await response.json()) as { tiers?: PricingTier[] };
  return data.tiers ?? [];
}

export async function startCheckout(tier: string, accessToken: string): Promise<void> {
  if (!PLATFORM_API_URL) {
    throw new Error("Billing is not configured for this environment.");
  }

  const response = await fetch(`${PLATFORM_API_URL}/payments/checkout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      tier,
      app_id: "checkyourdrawings",
      payment_type: "subscription",
    }),
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(detail.detail ?? "Could not start checkout.");
  }

  const session = (await response.json()) as CheckoutSession;
  await loadRazorpayScript();

  if (!window.Razorpay) {
    throw new Error("Razorpay checkout failed to load.");
  }

  if (!session.subscription_id) {
    throw new Error("Subscription checkout session is incomplete.");
  }

  const checkout = new window.Razorpay({
    key: session.key_id,
    name: "Check Your Drawings",
    description: session.description,
    subscription_id: session.subscription_id,
    prefill: session.prefill,
    theme: { color: "#111827" },
    handler: () => {
      window.location.assign(`${window.location.origin}/pricing?checkout=success`);
    },
  });
  checkout.open();
}

function loadRazorpayScript(): Promise<void> {
  if (window.Razorpay) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Razorpay checkout script."));
    document.body.appendChild(script);
  });
}
