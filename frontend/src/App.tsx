import { useState } from "react";

import { CompareButton } from "./components/CompareButton";
import { ResultViewer } from "./components/ResultViewer";
import { UploadPanel } from "./components/UploadPanel";
import type { CompareMetadata } from "./services/api";
import { uploadAndCompare } from "./services/api";


export default function App() {
  const [revisionA, setRevisionA] = useState<File | null>(null);
  const [revisionB, setRevisionB] = useState<File | null>(null);
  const [comparisonImageUrl, setComparisonImageUrl] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<CompareMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  async function handleCompare(): Promise<void> {
    if (revisionA === null || revisionB === null) {
      setError("Upload Revision A and Revision B before comparing.");
      return;
    }

    setIsComparing(true);
    setError(null);

    try {
      const result = await uploadAndCompare(revisionA, revisionB);
      setComparisonImageUrl(result.comparisonImageUrl);
      setMetadata(result.metadata);
    } catch (requestError) {
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
    <main className="app-shell">
      <header className="app-header">
        <h1>Check Your Drawings</h1>
        <p>Upload two drawing revisions and generate a visual comparison.</p>
      </header>

      <UploadPanel
        revisionA={revisionA}
        revisionB={revisionB}
        onRevisionAChange={setRevisionA}
        onRevisionBChange={setRevisionB}
      />

      <div className="compare-row">
        <CompareButton
          isLoading={isComparing}
          disabled={revisionA === null || revisionB === null}
          onClick={handleCompare}
        />
      </div>

      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}

      <section className="result-section" aria-label="Result">
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
              <dt>Detected regions</dt>
              <dd>{metadata.differences.regions.length}</dd>
            </div>

            <div>
              <dt>Changed pixels</dt>
              <dd>{metadata.differences.changed_pixel_count}</dd>
            </div>

            <div>
              <dt>Alignment inliers</dt>
              <dd>{metadata.alignment.inlier_matches}</dd>
            </div>
          </dl>
        </section>
      )}
    </main>
  );
}
