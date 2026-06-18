export const UPLOAD_DROP_HINT =
  "Drop a PDF here (plot or export from your design software)";

export const INVALID_FILE_TYPE_MESSAGE =
  "Unsupported file type. Upload a PDF exported or plotted from your design software.";

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
    return "Unsupported file content type. Upload a PDF.";
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "File exceeds the maximum size of 100 MB.";
  }

  return null;
}
