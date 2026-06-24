import { useEffect, useState } from "react";

import { AppLayout } from "../components/AppLayout";
import { trackEvent } from "../lib/analytics";
import { useAuth } from "../lib/auth-provider";
import { fetchPricingTiers, startCheckout, type PricingTier } from "../services/pricing";

function formatUsdCents(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

function tierLabel(tier: string): string {
  if (tier === "monthly") return "Pro Monthly";
  if (tier === "yearly") return "Pro Yearly";
  return tier;
}

export function PricingPage() {
  const { user, signIn, getAccessToken } = useAuth();
  const [tiers, setTiers] = useState<PricingTier[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingTier, setLoadingTier] = useState<string | null>(null);

  useEffect(() => {
    trackEvent("pricing_viewed");
    void fetchPricingTiers().then(setTiers);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("checkout") === "success") {
      trackEvent("checkout_completed");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  async function handleCheckout(tier: string): Promise<void> {
    setError(null);
    trackEvent("checkout_started", { tier });
    if (!user) {
      await signIn();
      return;
    }
    const token = getAccessToken();
    if (!token) {
      await signIn();
      return;
    }
    setLoadingTier(tier);
    try {
      await startCheckout(tier, token);
    } catch (checkoutError) {
      setError(
        checkoutError instanceof Error ? checkoutError.message : "Checkout failed.",
      );
    } finally {
      setLoadingTier(null);
    }
  }

  return (
    <AppLayout
      title="Pricing"
      subtitle="KVSHVL Pro — queue priority and more active jobs. Not larger uploads or feature gates."
    >
        <section className="pricing-intro">
          <p>
            <strong>Free (signed in):</strong> Unlimited comparisons, one active job at a time,
            standard queue. PDFs up to 100 MB each.
          </p>
          <p>
            <strong>Anonymous:</strong> Five successful comparisons without sign-in (one active job
            at a time), then Google sign-in to continue on the free tier.
          </p>
          <p>
            <strong>Pro:</strong> Unlimited comparisons, up to ten active jobs (pending or in
            progress), and queue priority. Same 100 MB per-PDF limit. Processing is serial — Pro
            lets you submit a backlog while earlier jobs run.
          </p>
        </section>

        {tiers.length > 0 ? (
          <div className="pricing-grid">
            {tiers.map((tier) => (
              <article key={tier.tier} className="pricing-card">
                <h2>{tierLabel(tier.tier)}</h2>
                <p className="pricing-amount">{formatUsdCents(tier.amount)}</p>
                <p className="pricing-note">
                  {tier.tier === "yearly" ? "Billed annually" : "Billed monthly"}
                </p>
                <button
                  type="button"
                  disabled={loadingTier === tier.tier}
                  onClick={() => void handleCheckout(tier.tier)}
                >
                  {loadingTier === tier.tier ? "Opening checkout…" : "Subscribe"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p>Billing is not configured for this environment.</p>
        )}

        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
    </AppLayout>
  );
}
