export const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"] as const;
export const ACCEPTED_MIME_TYPES = ["application/pdf", "image/png", "image/jpeg"] as const;
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
): mimeType is (typeof ACCEPTED_MIME_TYPES)[number] {
  return ACCEPTED_MIME_TYPES.includes(mimeType as (typeof ACCEPTED_MIME_TYPES)[number]);
}

export function validateFile(file: File): string | null {
  const extension = getFileExtension(file.name);

  if (!isAcceptedExtension(extension)) {
    return "Unsupported file type. Use PDF, PNG, JPG, or JPEG.";
  }

  if (file.type !== "" && !isAcceptedMimeType(file.type)) {
    return "Unsupported file content type. Use PDF, PNG, JPG, or JPEG.";
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "File exceeds the maximum size of 100 MB.";
  }

  return null;
}
