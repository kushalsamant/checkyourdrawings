import { useId, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import { validateFile } from "../utils/fileValidation";

const ACCEPT_ATTRIBUTE = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";

type RevisionKey = "revisionA" | "revisionB";

interface UploadPanelProps {
  revisionA: File | null;
  revisionB: File | null;
  onRevisionAChange: (file: File | null) => void;
  onRevisionBChange: (file: File | null) => void;
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
  revisionA,
  revisionB,
  onRevisionAChange,
  onRevisionBChange,
}: UploadPanelProps) {
  const generatedId = useId();
  const [draggingSlot, setDraggingSlot] = useState<RevisionKey | null>(null);
  const [errors, setErrors] = useState<Record<RevisionKey, string | null>>({
    revisionA: null,
    revisionB: null,
  });

  return (
    <section className="upload-panel" aria-label="Upload drawing revisions">
      <UploadSlot
        id={`${generatedId}-revision-a`}
        label="Revision A"
        file={revisionA}
        isDragging={draggingSlot === "revisionA"}
        error={errors.revisionA}
        onDragStateChange={(isDragging) => setDraggingSlot(isDragging ? "revisionA" : null)}
        onFileChange={onRevisionAChange}
        onErrorChange={(error) => setErrors((current) => ({ ...current, revisionA: error }))}
      />

      <UploadSlot
        id={`${generatedId}-revision-b`}
        label="Revision B"
        file={revisionB}
        isDragging={draggingSlot === "revisionB"}
        error={errors.revisionB}
        onDragStateChange={(isDragging) => setDraggingSlot(isDragging ? "revisionB" : null)}
        onFileChange={onRevisionBChange}
        onErrorChange={(error) => setErrors((current) => ({ ...current, revisionB: error }))}
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
        <span>{file ? file.name : "Drop a PDF, PNG, JPG, or JPEG file here"}</span>
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
