const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const COMPARE_TIMEOUT_MS = 5 * 60 * 1000;

export type DifferenceKind = "addition" | "deletion" | "modification";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DifferenceRegion {
  kind: DifferenceKind;
  bounding_box: BoundingBox;
  area: number;
  changed_pixels: number;
  addition_pixels: number;
  deletion_pixels: number;
  confidence: number;
}

export interface AlignmentMetadata {
  keypoints_reference: number;
  keypoints_revision: number;
  raw_matches: number;
  good_matches: number;
  inlier_matches: number;
  inlier_ratio: number;
  homography: number[][];
  output_width: number;
  output_height: number;
}

export interface DifferenceMetadata {
  width: number;
  height: number;
  regions: DifferenceRegion[];
  changed_pixel_count: number;
  changed_pixel_ratio: number;
}

export interface CompareMetadata {
  alignment: AlignmentMetadata;
  differences: DifferenceMetadata;
}

export interface CompareResponse {
  image_path: string;
  metadata: CompareMetadata;
}

export interface UploadAndCompareResult {
  comparisonImageUrl: string;
  metadata: CompareMetadata;
}

export async function uploadAndCompare(
  revisionA: File,
  revisionB: File,
  signal?: AbortSignal,
): Promise<UploadAndCompareResult> {
  const formData = new FormData();
  formData.append("revision_a", revisionA);
  formData.append("revision_b", revisionB);

  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), COMPARE_TIMEOUT_MS);

  const combinedSignal = signal
    ? mergeAbortSignals(signal, timeoutController.signal)
    : timeoutController.signal;

  try {
    const response = await fetch(`${API_BASE_URL}/compare`, {
      method: "POST",
      body: formData,
      signal: combinedSignal,
    });

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    const data = parseCompareResponse(await response.json());
    return {
      comparisonImageUrl: buildImageUrl(data.image_path),
      metadata: data.metadata,
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Comparison timed out. Try smaller files or try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function parseCompareResponse(data: unknown): CompareResponse {
  if (!isRecord(data)) {
    throw new Error("Comparison response was not a JSON object.");
  }

  if (typeof data.image_path !== "string" || data.image_path.length === 0) {
    throw new Error("Comparison response is missing image_path.");
  }

  if (!isRecord(data.metadata)) {
    throw new Error("Comparison response is missing metadata.");
  }

  const alignment = data.metadata.alignment;
  const differences = data.metadata.differences;

  if (!isRecord(alignment) || !isRecord(differences)) {
    throw new Error("Comparison metadata is incomplete.");
  }

  if (!Array.isArray(differences.regions)) {
    throw new Error("Comparison metadata is missing difference regions.");
  }

  return {
    image_path: data.image_path,
    metadata: data.metadata,
  } as unknown as CompareResponse;
}

export async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    const message = formatFastApiDetail(data.detail);
    if (message) {
      return message;
    }
  } catch {
    return `Request failed with status ${response.status}.`;
  }

  return `Request failed with status ${response.status}.`;
}

export function buildImageUrl(imagePath: string): string {
  if (/^https?:\/\//i.test(imagePath)) {
    const parsed = new URL(imagePath);
    const apiOrigin = new URL(API_BASE_URL).origin;
    if (parsed.origin !== apiOrigin) {
      throw new Error("Comparison image URL is not from the API origin.");
    }
    return imagePath;
  }

  return `${API_BASE_URL}/${imagePath.replace(/\\/g, "/").replace(/^\/+/, "")}`;
}

export async function downloadImageAsBlob(imageUrl: string): Promise<Blob> {
  const response = await fetch(imageUrl);
  if (!response.ok) {
    throw new Error("Failed to download comparison image.");
  }
  return response.blob();
}

function formatFastApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (isRecord(item) && typeof item.msg === "string") {
          return item.msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }

  if (isRecord(detail) && typeof detail.message === "string") {
    return detail.message;
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function mergeAbortSignals(first: AbortSignal, second: AbortSignal): AbortSignal {
  const controller = new AbortController();

  const abort = () => controller.abort();
  if (first.aborted || second.aborted) {
    controller.abort();
    return controller.signal;
  }

  first.addEventListener("abort", abort);
  second.addEventListener("abort", abort);
  return controller.signal;
}
