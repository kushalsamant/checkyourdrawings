export const UPLOAD_DROP_HINT = "Drop a PDF here.";

export const INVALID_FILE_TYPE_MESSAGE = "PDF only. Upload a plotted or exported drawing.";

export const ACCEPTED_EXTENSIONS = [".pdf"] as const;
export const ACCEPTED_MIME_TYPES = ["application/pdf"] as const;
export const MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024;

export function getFileExtension(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  if (dotIndex <= 0) {
    return "";
  }
  return filename.slice(dotIndex).toLowerCase();
}

export function isAcceptedExtension(
  extension: string,
): extension is (typeof ACCEPTED_EXTENSIONS)[number] {
  return ACCEPTED_EXTENSIONS.includes(extension as (typeof ACCEPTED_EXTENSIONS)[number]);
}

export function isAcceptedMimeType(
  mimeType: string,
  extension: string,
): boolean {
  if (mimeType === "" || mimeType === "application/octet-stream") {
    return isAcceptedExtension(extension);
  }

  return ACCEPTED_MIME_TYPES.includes(mimeType as (typeof ACCEPTED_MIME_TYPES)[number]);
}

export function validateFile(file: File): string | null {
  const extension = getFileExtension(file.name);

  if (!isAcceptedExtension(extension)) {
    return INVALID_FILE_TYPE_MESSAGE;
  }

  if (!isAcceptedMimeType(file.type, extension)) {
    return "Not a PDF. Upload a plotted or exported drawing.";
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "File exceeds 100 MB.";
  }

  return null;
}
