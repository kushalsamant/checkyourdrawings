import { useId, useRef, useState, type ChangeEvent } from "react";

import { trackEvent } from "../lib/analytics";
import type { CompareMetadata } from "../services/api";
import { downloadFileAsBlob, uploadAndCompare } from "../services/api";
import { ResultViewer } from "./ResultViewer";

export const MAX_BATCH_PAIRS = 20;

export interface BatchPair {
  id: string;
  drawingA: File;
  drawingB: File;
  labelA: string;
  labelB: string;
}

export type BatchPairStatus = "queued" | "running" | "done" | "error" | "cancelled";

export interface BatchPairResult {
  pair: BatchPair;
  status: BatchPairStatus;
  imageUrl: string | null;
  pdfUrl: string | null;
  metadata: CompareMetadata | null;
  error: string | null;
}

interface BatchPanelProps {
  canRunBatch: boolean;
  isSignedIn: boolean;
  onSignIn: () => void;
}

function makePairId(): string {
  return crypto.randomUUID();
}

export function BatchPanel({ canRunBatch, isSignedIn, onSignIn }: BatchPanelProps) {
  const [poolFiles, setPoolFiles] = useState<File[]>([]);
  const [selectedA, setSelectedA] = useState<string>("");
  const [selectedB, setSelectedB] = useState<string>("");
  const [pairs, setPairs] = useState<BatchPair[]>([]);
  const [results, setResults] = useState<BatchPairResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const cancelRef = useRef(false);
  const poolInputId = useId();

  function handlePoolChange(event: ChangeEvent<HTMLInputElement>): void {
    const selected = Array.from(event.target.files ?? []);
    setPoolFiles(selected);
    setSelectedA("");
    setSelectedB("");
  }

  function addPair(): void {
    if (selectedA === "" || selectedB === "") {
      return;
    }
    if (selectedA === selectedB) {
      return;
    }
    if (pairs.length >= MAX_BATCH_PAIRS) {
      return;
    }

    const fileA = poolFiles.find((file) => file.name === selectedA);
    const fileB = poolFiles.find((file) => file.name === selectedB);
    if (fileA === undefined || fileB === undefined) {
      return;
    }

    setPairs((current) => [
      ...current,
      {
        id: makePairId(),
        drawingA: fileA,
        drawingB: fileB,
        labelA: fileA.name,
        labelB: fileB.name,
      },
    ]);
    setSelectedA("");
    setSelectedB("");
  }

  function removePair(pairId: string): void {
    setPairs((current) => current.filter((pair) => pair.id !== pairId));
  }

  async function runBatch(): Promise<void> {
    if (!canRunBatch || pairs.length === 0 || isRunning) {
      return;
    }

    cancelRef.current = false;
    setIsRunning(true);
    setResults(
      pairs.map((pair) => ({
        pair,
        status: "queued",
        imageUrl: null,
        pdfUrl: null,
        metadata: null,
        error: null,
      })),
    );
    trackEvent("batch_start", { pair_count: pairs.length });

    const completed: BatchPairResult[] = [];

    for (let index = 0; index < pairs.length; index += 1) {
      if (cancelRef.current) {
        const cancelledTail = pairs.slice(index).map((pair) => ({
          pair,
          status: "cancelled" as const,
          imageUrl: null,
          pdfUrl: null,
          metadata: null,
          error: "Cancelled.",
        }));
        setResults([...completed, ...cancelledTail]);
        break;
      }

      const pair = pairs[index];
      setProgress(`Running ${index + 1} of ${pairs.length}...`);
      setResults((current) =>
        current.map((item, itemIndex) =>
          itemIndex === index ? { ...item, status: "running" } : item,
        ),
      );

      try {
        const result = await uploadAndCompare(pair.drawingA, pair.drawingB);
        const doneResult: BatchPairResult = {
          pair,
          status: "done",
          imageUrl: result.comparisonImageUrl,
          pdfUrl: result.comparisonPdfUrl,
          metadata: result.metadata,
          error: null,
        };
        completed.push(doneResult);
        setResults((current) =>
          current.map((item, itemIndex) => (itemIndex === index ? doneResult : item)),
        );
      } catch (error) {
        const failedResult: BatchPairResult = {
          pair,
          status: "error",
          imageUrl: null,
          pdfUrl: null,
          metadata: null,
          error: error instanceof Error ? error.message : "Comparison failed.",
        };
        completed.push(failedResult);
        setResults((current) =>
          current.map((item, itemIndex) => (itemIndex === index ? failedResult : item)),
        );
      }
    }

    setProgress(null);
    setIsRunning(false);
    trackEvent("batch_complete", { pair_count: pairs.length });
  }

  function cancelBatch(): void {
    cancelRef.current = true;
  }

  async function downloadZip(): Promise<void> {
    const doneResults = results.filter(
      (result) => result.status === "done" && result.pdfUrl !== null,
    );
    if (doneResults.length === 0) {
      return;
    }

    const JSZip = (await import("jszip")).default;
    const zip = new JSZip();

    for (const result of doneResults) {
      if (result.pdfUrl === null) {
        continue;
      }
      const blob = await downloadFileAsBlob(result.pdfUrl);
      const safeName = `${result.pair.labelA}__${result.pair.labelB}`.replace(/[^\w.-]+/g, "_");
      zip.file(`${safeName}.pdf`, blob);
    }

    const zipBlob = await zip.generateAsync({ type: "blob" });
    const objectUrl = URL.createObjectURL(zipBlob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = "checkyourdrawings-batch.zip";
    link.click();
    URL.revokeObjectURL(objectUrl);
    trackEvent("batch_pdf_zip_download", { file_count: doneResults.length });
  }

  if (!isSignedIn) {
    return (
      <section className="batch-panel" aria-label="Batch compare">
        <p>Batch compare requires a paid subscription.</p>
        <button type="button" onClick={onSignIn}>
          Sign in
        </button>
      </section>
    );
  }

  if (!canRunBatch) {
    return (
      <section className="batch-panel" aria-label="Batch compare">
        <p>Batch compare is included with a paid subscription.</p>
      </section>
    );
  }

  const doneCount = results.filter((result) => result.status === "done").length;

  return (
    <section className="batch-panel" aria-label="Batch compare">
      <div className="batch-section">
        <h2>File pool</h2>
        <label htmlFor={poolInputId}>Add PDFs for this batch</label>
        <input
          id={poolInputId}
          type="file"
          accept=".pdf,application/pdf"
          multiple
          onChange={handlePoolChange}
        />
        {poolFiles.length > 0 && <p>{poolFiles.length} file(s) in pool</p>}
      </div>

      <div className="batch-section">
        <h2>Build pairs</h2>
        <div className="batch-pair-builder">
          <select value={selectedA} onChange={(event) => setSelectedA(event.target.value)}>
            <option value="">Drawing A</option>
            {poolFiles.map((file) => (
              <option key={`a-${file.name}`} value={file.name}>
                {file.name}
              </option>
            ))}
          </select>
          <select value={selectedB} onChange={(event) => setSelectedB(event.target.value)}>
            <option value="">Drawing B</option>
            {poolFiles.map((file) => (
              <option key={`b-${file.name}`} value={file.name}>
                {file.name}
              </option>
            ))}
          </select>
          <button type="button" onClick={addPair} disabled={selectedA === "" || selectedB === ""}>
            Add pair
          </button>
        </div>
      </div>

      {pairs.length > 0 && (
        <div className="batch-section">
          <h2>Queue ({pairs.length})</h2>
          <ul className="batch-queue">
            {pairs.map((pair) => (
              <li key={pair.id}>
                <span>
                  {pair.labelA} ↔ {pair.labelB}
                </span>
                <button type="button" onClick={() => removePair(pair.id)} disabled={isRunning}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <div className="batch-actions">
            <button type="button" onClick={() => void runBatch()} disabled={isRunning}>
              {isRunning ? "Running batch..." : "Run batch"}
            </button>
            {isRunning && (
              <button type="button" onClick={cancelBatch}>
                Cancel
              </button>
            )}
          </div>
          {progress && <p role="status">{progress}</p>}
        </div>
      )}

      {results.length > 0 && (
        <div className="batch-section">
          <div className="batch-results-header">
            <h2>
              Results ({doneCount}/{results.length})
            </h2>
            {doneCount > 0 && (
              <button type="button" onClick={() => void downloadZip()}>
                Download ZIP
              </button>
            )}
          </div>
          {results.map((result) => (
            <article key={result.pair.id} className="batch-result-card">
              <header>
                <strong>
                  {result.pair.labelA} ↔ {result.pair.labelB}
                </strong>
                <span className={`batch-status batch-status--${result.status}`}>
                  {result.status}
                </span>
              </header>
              {result.error && <p className="alert">{result.error}</p>}
              {result.imageUrl && result.pdfUrl && (
                <ResultViewer
                  imageUrl={result.imageUrl}
                  pdfUrl={result.pdfUrl}
                  pngFilename={`${result.pair.labelA}__${result.pair.labelB}.png`}
                  pdfFilename={`${result.pair.labelA}__${result.pair.labelB}.pdf`}
                  altText={`Batch result for ${result.pair.labelA} and ${result.pair.labelB}`}
                />
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
