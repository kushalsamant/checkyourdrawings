import { useEffect, useRef, useState } from "react";

import { PlatformAppLayout } from "./components/PlatformAppLayout";
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
  const { user, loading: authLoading, signIn } = useAuth();
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
    if (authLoading) {
      return;
    }

    const controller = new AbortController();
    void fetchAllowance(Boolean(user), controller.signal).then((status) => {
      if (!controller.signal.aborted) {
        setAllowance(status);
      }
    });

    return () => {
      controller.abort();
    };
  }, [user, authLoading]);

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
      setError("Upload Drawing A and Drawing B first.");
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
      void fetchAllowance(Boolean(user)).then(setAllowance);
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
          : "Comparison failed. Try again.",
      );
    } finally {
      setIsComparing(false);
    }
  }

  return (
    <PlatformAppLayout>
        {allowance?.tier === "anonymous" &&
          allowance.remaining !== null &&
          allowance.total !== null && (
            <p className="allowance-notice" role="status">
              {allowance.remaining} of {allowance.total} free comparisons left
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
            Aligning and comparing… Large PDFs may take several minutes.
          </p>
        )}

        <div className="compare-row">
          <CompareButton
            isLoading={isComparing}
            disabled={drawingA === null || drawingB === null}
            isPrimary={
              drawingA !== null &&
              drawingB !== null &&
              comparisonImageUrl === null &&
              !isComparing
            }
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
              "Alignment confidence is low. Review the overlay manually."}
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
            <p>No overlay yet. Upload two PDFs and compare.</p>
          )}
        </section>

        {metadata && (
          <section className="metadata-section" aria-label="Comparison metadata">
            <h2>Metadata</h2>
            <dl className="metadata-grid">
              <div>
                <dt>Orange — removals</dt>
                <dd>{metadata.overlay.orange_pixels}</dd>
              </div>

              <div>
                <dt>Blue — additions</dt>
                <dd>{metadata.overlay.blue_pixels}</dd>
              </div>

              <div>
                <dt>Green — matching</dt>
                <dd>{metadata.overlay.green_pixels}</dd>
              </div>

              <div>
                <dt>Red — overlap</dt>
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
    </PlatformAppLayout>
  );
}
