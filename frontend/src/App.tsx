import { useEffect, useRef, useState } from "react";

import { BatchPanel } from "./components/BatchPanel";
import { CompareButton } from "./components/CompareButton";
import { ResultViewer } from "./components/ResultViewer";
import { UploadPanel } from "./components/UploadPanel";
import { trackEvent } from "./lib/analytics";
import { isAuthConfigured, useAuth } from "./lib/auth-provider";
import type { AccountStatus, CompareMetadata } from "./services/api";
import { CHECKYOURDRAWINGS_SITE_URL, KVSHVL_PRIVACY_URL, KVSHVL_TERMS_URL } from "./lib/legal-urls";
import { fetchAccountStatus, getUpgradeUrl, uploadAndCompare } from "./services/api";

type AppMode = "single" | "batch";

export default function App() {
  const authConfigured = isAuthConfigured();
  const { user, loading: authLoading, signIn, signOut } = useAuth();
  const [mode, setMode] = useState<AppMode>("single");
  const [account, setAccount] = useState<AccountStatus | null>(null);
  const [drawingA, setDrawingA] = useState<File | null>(null);
  const [drawingB, setDrawingB] = useState<File | null>(null);
  const [comparisonImageUrl, setComparisonImageUrl] = useState<string | null>(null);
  const [comparisonPdfUrl, setComparisonPdfUrl] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<CompareMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setComparisonImageUrl(null);
    setComparisonPdfUrl(null);
    setMetadata(null);
    setError(null);
  }, [drawingA, drawingB]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadAccountStatus(): Promise<void> {
      if (!authConfigured || !user) {
        setAccount({ signed_in: false, paid: false, email: null });
        return;
      }

      const status = await fetchAccountStatus();
      if (!cancelled) {
        setAccount(status);
      }
    }

    void loadAccountStatus();

    return () => {
      cancelled = true;
    };
  }, [authConfigured, user]);

  async function handleCompare(): Promise<void> {
    if (drawingA === null || drawingB === null) {
      setError("Upload Drawing A and Drawing B before comparing.");
      return;
    }

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsComparing(true);
    setError(null);
    trackEvent("compare_start");

    try {
      const result = await uploadAndCompare(drawingA, drawingB, abortController.signal);
      setComparisonImageUrl(result.comparisonImageUrl);
      setComparisonPdfUrl(result.comparisonPdfUrl);
      setMetadata(result.metadata);
      trackEvent("compare_success");
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") {
        return;
      }

      setComparisonImageUrl(null);
      setComparisonPdfUrl(null);
      setMetadata(null);
      trackEvent("compare_fail");
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Comparison failed. Please try again.",
      );
    } finally {
      setIsComparing(false);
    }
  }

  const canRunBatch = account?.paid === true;

  return (
    <div className="page-body">
      <main className="app-shell">
        <header className="app-header">
          <div className="app-header-row">
            <div>
              <h1>Check Your Drawings</h1>
              <p>Upload two PDF drawings for an auto-aligned coordination overlay.</p>
            </div>

            <div className="auth-actions">
              <a
                href={`${CHECKYOURDRAWINGS_SITE_URL}/about`}
                className="header-link"
                target="_blank"
                rel="noreferrer"
              >
                About
              </a>
              {authConfigured &&
                (authLoading ? (
                  <span>Checking session...</span>
                ) : user ? (
                  <>
                    <span className="auth-email">{user.email}</span>
                    <button type="button" onClick={() => void signOut()}>
                      Sign out
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => void signIn()}>
                    Sign in
                  </button>
                ))}
            </div>
          </div>
        </header>

        <div className="mode-toggle" role="tablist" aria-label="Compare mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "single"}
            className={mode === "single" ? "mode-toggle__button is-active" : "mode-toggle__button"}
            onClick={() => setMode("single")}
          >
            Single pair
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "batch"}
            className={mode === "batch" ? "mode-toggle__button is-active" : "mode-toggle__button"}
            onClick={() => setMode("batch")}
          >
            Batch
          </button>
        </div>

        {mode === "single" ? (
          <>
            <UploadPanel
              drawingA={drawingA}
              drawingB={drawingB}
              onDrawingAChange={setDrawingA}
              onDrawingBChange={setDrawingB}
            />

            <div className="compare-row">
              <CompareButton
                isLoading={isComparing}
                disabled={drawingA === null || drawingB === null}
                onClick={handleCompare}
              />
            </div>

            {error && (
              <p className="alert" role="alert">
                {error}
                {error.includes("subscription required") && (
                  <>
                    {" "}
                    <a href={getUpgradeUrl()} target="_blank" rel="noreferrer">
                      Upgrade on kvshvl.in
                    </a>
                  </>
                )}
              </p>
            )}

            {metadata?.alignment_confidence.status === "marginal" && (
              <p className="warning" role="status">
                {metadata.alignment_confidence.message ??
                  "Alignment confidence is low. Review the comparison manually."}
              </p>
            )}

            <section className="result-section" aria-label="Result" aria-live="polite">
              <h2>Result</h2>

              {comparisonImageUrl && comparisonPdfUrl ? (
                <ResultViewer
                  imageUrl={comparisonImageUrl}
                  pdfUrl={comparisonPdfUrl}
                  showUpsell={!account?.paid}
                />
              ) : (
                <p>No comparison result yet.</p>
              )}
            </section>

            {metadata && (
              <section className="metadata-section" aria-label="Comparison metadata">
                <h2>Metadata</h2>
                <dl className="metadata-grid">
                  <div>
                    <dt>Orange (only A)</dt>
                    <dd>{metadata.overlay.orange_pixels}</dd>
                  </div>

                  <div>
                    <dt>Blue (only B)</dt>
                    <dd>{metadata.overlay.blue_pixels}</dd>
                  </div>

                  <div>
                    <dt>Green (both)</dt>
                    <dd>{metadata.overlay.green_pixels}</dd>
                  </div>

                  <div>
                    <dt>Red (clash)</dt>
                    <dd>{metadata.overlay.red_pixels}</dd>
                  </div>

                  <div>
                    <dt>Alignment inliers</dt>
                    <dd>{metadata.alignment.inlier_matches}</dd>
                  </div>

                  <div>
                    <dt>Alignment confidence</dt>
                    <dd>{metadata.alignment_confidence.status}</dd>
                  </div>

                  <div>
                    <dt>Overlap area</dt>
                    <dd>
                      {metadata.content.overlap_bbox.width} x {metadata.content.overlap_bbox.height}
                    </dd>
                  </div>

                  <div>
                    <dt>Inlier ratio</dt>
                    <dd>{metadata.alignment.inlier_ratio.toFixed(2)}</dd>
                  </div>
                </dl>
              </section>
            )}
          </>
        ) : (
          <BatchPanel
            canRunBatch={canRunBatch}
            isSignedIn={Boolean(user)}
            onSignIn={() => void signIn()}
          />
        )}

        <footer className="app-footer">
          <p>
            <a href={KVSHVL_PRIVACY_URL} target="_blank" rel="noreferrer">
              Privacy Policy
            </a>
            {" · "}
            <a href={KVSHVL_TERMS_URL} target="_blank" rel="noreferrer">
              Terms of Service
            </a>
          </p>
          <p>&copy; {new Date().getFullYear()} Check Your Drawings</p>
        </footer>
      </main>
    </div>
  );
}
