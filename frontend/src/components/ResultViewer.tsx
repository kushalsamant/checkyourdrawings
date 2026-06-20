import { useState } from "react";

import { downloadFileAsBlob, getUpgradeUrl } from "../services/api";

interface ResultViewerProps {
  imageUrl: string;
  pdfUrl: string;
  pngFilename?: string;
  pdfFilename?: string;
  altText?: string;
  showUpsell?: boolean;
}

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.25;

export function ResultViewer({
  imageUrl,
  pdfUrl,
  pngFilename = "comparison-result.png",
  pdfFilename = "comparison-result.pdf",
  altText = "Rendered drawing comparison result",
  showUpsell = false,
}: ResultViewerProps) {
  const [zoom, setZoom] = useState<number>(1);
  const [imageError, setImageError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"pdf" | "png" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  function zoomOut(): void {
    setZoom((currentZoom) => Math.max(MIN_ZOOM, currentZoom - ZOOM_STEP));
  }

  function zoomIn(): void {
    setZoom((currentZoom) => Math.min(MAX_ZOOM, currentZoom + ZOOM_STEP));
  }

  function resetZoom(): void {
    setZoom(1);
  }

  async function handleDownload(kind: "pdf" | "png"): Promise<void> {
    setDownloading(kind);
    setDownloadError(null);

    const url = kind === "pdf" ? pdfUrl : imageUrl;
    const filename = kind === "pdf" ? pdfFilename : pngFilename;

    try {
      const blob = await downloadFileAsBlob(url);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch {
      setDownloadError("Download failed. Open the file in a new tab and save it manually.");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div aria-label="Comparison result">
      <div className="result-toolbar">
        <button
          type="button"
          onClick={zoomOut}
          disabled={zoom <= MIN_ZOOM}
          aria-label="Zoom out"
        >
          Zoom out
        </button>
        <button
          type="button"
          onClick={resetZoom}
          disabled={zoom === 1}
          aria-label={`Reset zoom to 100 percent, currently ${Math.round(zoom * 100)} percent`}
        >
          {Math.round(zoom * 100)}%
        </button>
        <button
          type="button"
          onClick={zoomIn}
          disabled={zoom >= MAX_ZOOM}
          aria-label="Zoom in"
        >
          Zoom in
        </button>
        <button
          type="button"
          className="download-link"
          onClick={() => void handleDownload("pdf")}
          disabled={downloading !== null}
          aria-label="Download comparison PDF"
        >
          {downloading === "pdf" ? "Downloading..." : "Download PDF"}
        </button>
        <button
          type="button"
          className="download-link"
          onClick={() => void handleDownload("png")}
          disabled={downloading !== null}
          aria-label="Download comparison PNG"
        >
          {downloading === "png" ? "Downloading..." : "Download PNG"}
        </button>
      </div>

      <p className="retention-notice" role="note">
        Download to keep a copy — results aren&apos;t stored permanently.
      </p>

      {showUpsell && (
        <p className="upsell-banner" role="status">
          Comparing a full revision set?{" "}
          <a href={getUpgradeUrl()} target="_blank" rel="noreferrer">
            Subscribe on kvshvl.in for batch compare
          </a>
        </p>
      )}

      {downloadError && (
        <p className="alert" role="alert">
          {downloadError}
        </p>
      )}

      <div className="image-stage">
        {imageError ? (
          <p className="alert" role="alert">
            {imageError}
          </p>
        ) : (
          <img
            className="result-image"
            src={imageUrl}
            alt={altText}
            style={{
              width: `${zoom * 100}%`,
            }}
            onError={() => {
              setImageError("Failed to load comparison image.");
            }}
          />
        )}
      </div>
    </div>
  );
}
