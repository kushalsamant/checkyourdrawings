import { useId, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import { validateFile } from "../utils/fileValidation";

const ACCEPT_ATTRIBUTE = ".pdf,.png,.jpg,.jpeg,.dwg,application/pdf,image/png,image/jpeg,application/octet-stream";

type DrawingKey = "drawingA" | "drawingB";

interface UploadPanelProps {
  drawingA: File | null;
  drawingB: File | null;
  onDrawingAChange: (file: File | null) => void;
  onDrawingBChange: (file: File | null) => void;
}

interface UploadSlotProps {
  id: string;
  label: string;
  file: File | null;
  isDragging: boolean;
  error: string | null;
  onDragStateChange: (isDragging: boolean) => void;
  onFileChange: (file: File | null) => void;
  onErrorChange: (error: string | null) => void;
}

export function UploadPanel({
  drawingA,
  drawingB,
  onDrawingAChange,
  onDrawingBChange,
}: UploadPanelProps) {
  const generatedId = useId();
  const [draggingSlot, setDraggingSlot] = useState<DrawingKey | null>(null);
  const [errors, setErrors] = useState<Record<DrawingKey, string | null>>({
    drawingA: null,
    drawingB: null,
  });

  return (
    <section className="upload-panel" aria-label="Upload drawings">
      <UploadSlot
        id={`${generatedId}-drawing-a`}
        label="Drawing A"
        file={drawingA}
        isDragging={draggingSlot === "drawingA"}
        error={errors.drawingA}
        onDragStateChange={(isDragging) => setDraggingSlot(isDragging ? "drawingA" : null)}
        onFileChange={onDrawingAChange}
        onErrorChange={(error) => setErrors((current) => ({ ...current, drawingA: error }))}
      />

      <UploadSlot
        id={`${generatedId}-drawing-b`}
        label="Drawing B"
        file={drawingB}
        isDragging={draggingSlot === "drawingB"}
        error={errors.drawingB}
        onDragStateChange={(isDragging) => setDraggingSlot(isDragging ? "drawingB" : null)}
        onFileChange={onDrawingBChange}
        onErrorChange={(error) => setErrors((current) => ({ ...current, drawingB: error }))}
      />
    </section>
  );
}

function UploadSlot({
  id,
  label,
  file,
  isDragging,
  error,
  onDragStateChange,
  onFileChange,
  onErrorChange,
}: UploadSlotProps) {
  function handleSelectedFile(selectedFile: File | null): void {
    if (selectedFile === null) {
      onFileChange(null);
      onErrorChange(null);
      return;
    }

    const validationError = validateFile(selectedFile);
    if (validationError !== null) {
      onFileChange(null);
      onErrorChange(validationError);
      return;
    }

    onFileChange(selectedFile);
    onErrorChange(null);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>): void {
    handleSelectedFile(event.target.files?.[0] ?? null);
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    onDragStateChange(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    onDragStateChange(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    onDragStateChange(false);
    handleSelectedFile(event.dataTransfer.files.item(0));
  }

  return (
    <div className="upload-slot">
      <label
        className="drop-zone"
        htmlFor={id}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-dragging={isDragging}
      >
        <strong>{label}</strong>
        <span>{file ? file.name : "Drop a PDF, PNG, JPG, JPEG, or DWG file here"}</span>
      </label>

      <input
        className="file-input"
        id={id}
        type="file"
        accept={ACCEPT_ATTRIBUTE}
        onChange={handleInputChange}
      />

      {file && (
        <button type="button" onClick={() => handleSelectedFile(null)}>
          Remove {label}
        </button>
      )}

      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
