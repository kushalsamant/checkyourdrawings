import { useEffect, useState } from "react";

import { PlatformAppLayout } from "../components/PlatformAppLayout";
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
    <PlatformAppLayout
      title="Need more active jobs?"
      subtitle="Pro adds queue priority. Upload limits stay the same."
    >
        <section className="pricing-intro">
          <ul>
            <li>
              <strong>Free:</strong> Unlimited comparisons. One active job. PDFs up to 100 MB.
            </li>
            <li>
              <strong>Anonymous:</strong> Five comparisons without sign-in. One active job.
            </li>
            <li>
              <strong>Pro:</strong> Ten active jobs. Queue priority. Same 100 MB limit.
            </li>
          </ul>
          <p>
            <strong>KVSHVL Pro is one subscription per account.</strong> It is not limited to
            this app. Pro today includes <strong>Check Your Drawings</strong> and{" "}
            <strong>Coherence</strong>.
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
          <p>Billing is not configured here.</p>
        )}

        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
    </PlatformAppLayout>
  );
}
