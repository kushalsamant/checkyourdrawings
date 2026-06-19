import { useEffect, useRef, useState } from "react";

import { CompareButton } from "./components/CompareButton";
import { ResultViewer } from "./components/ResultViewer";
import { UploadPanel } from "./components/UploadPanel";
import { isAuthConfigured, useAuth } from "./lib/auth-provider";
import type { CompareMetadata } from "./services/api";
import { getUpgradeUrl, uploadAndCompare } from "./services/api";


export default function App() {
  const authConfigured = isAuthConfigured();
  const { user, loading: authLoading, signIn, signOut } = useAuth();
  const [drawingA, setDrawingA] = useState<File | null>(null);
  const [drawingB, setDrawingB] = useState<File | null>(null);
  const [comparisonImageUrl, setComparisonImageUrl] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<CompareMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setComparisonImageUrl(null);
    setMetadata(null);
    setError(null);
  }, [drawingA, drawingB]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

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

    try {
      const result = await uploadAndCompare(drawingA, drawingB, abortController.signal);
      setComparisonImageUrl(result.comparisonImageUrl);
      setMetadata(result.metadata);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") {
        return;
      }

      setComparisonImageUrl(null);
      setMetadata(null);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Comparison failed. Please try again.",
      );
    } finally {
      setIsComparing(false);
    }
  }

  return (
    <div className="page-body">
      <main className="app-shell">
        <header className="app-header">
        <div className="app-header-row">
          <div>
            <h1>Check Your Drawings</h1>
            <p>Upload two PDF drawings for an auto-aligned coordination overlay.</p>
          </div>

          {authConfigured && (
            <div className="auth-actions">
              {authLoading ? (
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
              )}
            </div>
          )}
        </div>
      </header>

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

        {comparisonImageUrl ? (
          <ResultViewer imageUrl={comparisonImageUrl} />
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

        <footer className="app-footer">
          <p>&copy; {new Date().getFullYear()} Check Your Drawings</p>
        </footer>
      </main>
    </div>
  );
}
