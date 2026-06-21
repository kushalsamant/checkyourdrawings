import { useEffect, useState } from "react";

import { useAuth } from "../lib/auth-provider";
import { fetchPricingTiers, startCheckout, type PricingTier } from "../services/pricing";

function formatInrPaise(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount / 100);
}

export function PricingPanel() {
  const { user, signIn, getAccessToken } = useAuth();
  const [tiers, setTiers] = useState<PricingTier[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingTier, setLoadingTier] = useState<string | null>(null);

  useEffect(() => {
    void fetchPricingTiers().then(setTiers);
  }, []);

  if (tiers.length === 0) {
    return null;
  }

  async function handleCheckout(tier: string): Promise<void> {
    setError(null);
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
    <section className="pricing-section" aria-label="Pricing">
      <h2>Upgrade</h2>
      <div className="pricing-grid">
        {tiers.map((tier) => (
          <article key={tier.tier} className="pricing-card">
            <h3>{tier.tier}</h3>
            <p>{formatInrPaise(tier.amount)}</p>
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
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
