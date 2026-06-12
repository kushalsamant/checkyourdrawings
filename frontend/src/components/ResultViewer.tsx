import { useState } from "react";

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

  function zoomOut(): void {
    setZoom((currentZoom) => Math.max(MIN_ZOOM, currentZoom - ZOOM_STEP));
  }

  function zoomIn(): void {
    setZoom((currentZoom) => Math.min(MAX_ZOOM, currentZoom + ZOOM_STEP));
  }

  function resetZoom(): void {
    setZoom(1);
  }

  return (
    <section aria-label="Comparison result">
      <div className="result-toolbar">
        <button type="button" onClick={zoomOut} disabled={zoom <= MIN_ZOOM}>
          Zoom out
        </button>
        <button type="button" onClick={resetZoom} disabled={zoom === 1}>
          {Math.round(zoom * 100)}%
        </button>
        <button type="button" onClick={zoomIn} disabled={zoom >= MAX_ZOOM}>
          Zoom in
        </button>
        <a className="download-link" href={imageUrl} download={filename}>
          Download
        </a>
      </div>

      <div className="image-stage">
        <img
          className="result-image"
          src={imageUrl}
          alt={altText}
          style={{
            width: `${zoom * 100}%`,
          }}
        />
      </div>
    </section>
  );
}
