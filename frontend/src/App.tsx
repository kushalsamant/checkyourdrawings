import { useEffect, useRef, useState } from "react";

import { AppHeader } from "./components/AppHeader";
import { CompareButton } from "./components/CompareButton";
import { ResultViewer } from "./components/ResultViewer";
import { UploadPanel } from "./components/UploadPanel";
import { trackEvent } from "./lib/analytics";
import { useAuth } from "./lib/auth-provider";
import type { AllowanceStatus, CompareMetadata } from "./services/api";
import {
  fetchAllowance,
  SignInRequiredError,
  uploadAndCompare,
} from "./services/api";

export default function App() {
  const { user, signIn } = useAuth();
  const [drawingA, setDrawingA] = useState<File | null>(null);
  const [drawingB, setDrawingB] = useState<File | null>(null);
  const [comparisonImageUrl, setComparisonImageUrl] = useState<string | null>(null);
  const [comparisonPdfUrl, setComparisonPdfUrl] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<CompareMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [allowance, setAllowance] = useState<AllowanceStatus | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    void fetchAllowance().then(setAllowance);
  }, [user]);

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
      void fetchAllowance().then(setAllowance);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") {
        return;
      }

      if (requestError instanceof SignInRequiredError) {
        await signIn();
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

  return (
    <div className="page-body">
      <main className="app-shell">
        <AppHeader />

        {allowance?.tier === "anonymous" &&
          allowance.remaining !== null &&
          allowance.total !== null && (
            <p className="allowance-notice" role="status">
              {allowance.remaining} of {allowance.total} free comparisons remaining
            </p>
          )}

        <UploadPanel
          drawingA={drawingA}
          drawingB={drawingB}
          onDrawingAChange={setDrawingA}
          onDrawingBChange={setDrawingB}
        />

        {isComparing && (
          <p className="status" role="status">
            Comparing drawings… This can take a few minutes for large PDFs.
          </p>
        )}

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
      </main>
    </div>
  );
}
