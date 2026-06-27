import { useEffect, useState } from "react";

import { PlatformAppLayout } from "../components/PlatformAppLayout";
import { trackEvent } from "../lib/analytics";
import { useAuth } from "../lib/auth-provider";
import {
  cancelSubscription,
  fetchAccountDetails,
  type AccountDetails,
} from "../services/account";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function AccountPage() {
  const { user, loading: authLoading, signIn, signOut } = useAuth();
  const [account, setAccount] = useState<AccountDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    trackEvent("account_viewed");
  }, []);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!user) {
      setAccount(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    void fetchAccountDetails()
      .then(setAccount)
      .catch((fetchError) => {
        setError(
          fetchError instanceof Error ? fetchError.message : "Could not load account.",
        );
      })
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  async function handleCancel(): Promise<void> {
    setError(null);
    setCancelling(true);
    try {
      await cancelSubscription();
      trackEvent("subscription_cancelled");
      const refreshed = await fetchAccountDetails();
      setAccount(refreshed);
    } catch (cancelError) {
      setError(
        cancelError instanceof Error ? cancelError.message : "Could not cancel subscription.",
      );
    } finally {
      setCancelling(false);
    }
  }

  const expiresLabel = formatDate(account?.subscription_expires_at ?? null);

  return (
    <PlatformAppLayout title="Account" subtitle="Your plan and subscription.">
        {authLoading || loading ? (
          <p role="status">Loading…</p>
        ) : !user ? (
          <section className="account-panel">
            <p>Sign in to view your plan.</p>
            <button type="button" className="action-primary" onClick={() => void signIn()}>
              Sign in with Google
            </button>
          </section>
        ) : (
          <section className="account-panel">
            <dl className="account-details">
              <div>
                <dt>Email</dt>
                <dd>{account?.email ?? user.email}</dd>
              </div>
              {account?.name && (
                <div>
                  <dt>Name</dt>
                  <dd>{account.name}</dd>
                </div>
              )}
              <div>
                <dt>Plan</dt>
                <dd>{account?.paid ? "KVSHVL Pro" : "Free"}</dd>
              </div>
              {account?.subscription_tier && account.paid && (
                <div>
                  <dt>Billing cycle</dt>
                  <dd>{account.subscription_tier === "yearly" ? "Yearly" : "Monthly"}</dd>
                </div>
              )}
              {account?.subscription_status && (
                <div>
                  <dt>Status</dt>
                  <dd>{account.subscription_status}</dd>
                </div>
              )}
              {expiresLabel && (
                <div>
                  <dt>{account?.subscription_auto_renew ? "Renews" : "Access until"}</dt>
                  <dd>{expiresLabel}</dd>
                </div>
              )}
            </dl>

            {!account?.paid && (
              <p>
                Pro adds queue priority and up to ten active jobs. One subscription also unlocks{" "}
                <strong>Coherence</strong>.
              </p>
            )}

            {account?.paid && (
              <p>
                Your KVSHVL Pro subscription is active on this account. Includes Pro in{" "}
                <strong>Check Your Drawings</strong> and <strong>Coherence</strong>.
              </p>
            )}

            {account?.has_subscription && account.subscription_auto_renew && (
              <button
                type="button"
                className="button-subtle"
                disabled={cancelling}
                onClick={() => void handleCancel()}
              >
                {cancelling ? "Cancelling…" : "Cancel subscription"}
              </button>
            )}

            <button type="button" className="button-subtle" onClick={() => void signOut()}>
              Sign out
            </button>
          </section>
        )}

        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
    </PlatformAppLayout>
  );
}
