import { useId, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"] as const;
const ACCEPTED_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg"] as const;
const ACCEPT_ATTRIBUTE = [...ACCEPTED_EXTENSIONS, ...ACCEPTED_MIME_TYPES].join(",");

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

function validateFile(file: File): string | null {
  const extension = getFileExtension(file.name);

  if (!isAcceptedExtension(extension)) {
    return "Unsupported file type. Use PDF, PNG, JPG, or JPEG.";
  }

  if (file.type !== "" && !isAcceptedMimeType(file.type)) {
    return "Unsupported file content type. Use PDF, PNG, JPG, or JPEG.";
  }

  return null;
}

function getFileExtension(filename: string): string {
  const extension = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  return extension;
}

function isAcceptedExtension(extension: string): extension is (typeof ACCEPTED_EXTENSIONS)[number] {
  return ACCEPTED_EXTENSIONS.includes(extension as (typeof ACCEPTED_EXTENSIONS)[number]);
}

function isAcceptedMimeType(mimeType: string): mimeType is (typeof ACCEPTED_MIME_TYPES)[number] {
  return ACCEPTED_MIME_TYPES.includes(mimeType as (typeof ACCEPTED_MIME_TYPES)[number]);
}
