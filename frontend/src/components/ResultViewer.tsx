import { useState } from "react";

import { downloadImageAsBlob } from "../services/api";

interface ResultViewerProps {
  imageUrl: string;
  filename?: string;
  altText?: string;
}

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.25;

export function ResultViewer({
  imageUrl,
  filename = "comparison-result.png",
  altText = "Rendered drawing comparison result",
}: ResultViewerProps) {
  const [zoom, setZoom] = useState<number>(1);
  const [imageError, setImageError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
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

  async function handleDownload(): Promise<void> {
    setIsDownloading(true);
    setDownloadError(null);

    try {
      const blob = await downloadImageAsBlob(imageUrl);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch {
      setDownloadError("Download failed. Open the image in a new tab and save it manually.");
    } finally {
      setIsDownloading(false);
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
          onClick={handleDownload}
          disabled={isDownloading}
          aria-label="Download comparison image"
        >
          {isDownloading ? "Downloading..." : "Download"}
        </button>
      </div>

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
            onError={() => setImageError("Failed to load comparison image.")}
          />
        )}
      </div>
    </div>
  );
}
