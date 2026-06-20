import { getAuthAccessToken } from "../lib/auth-provider";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const UPGRADE_URL =
  (import.meta.env.VITE_KVSHVL_UPGRADE_URL ?? "https://kvshvl.in").replace(/\/$/, "");
const COMPARE_TIMEOUT_MS = 5 * 60 * 1000;
const COMPARE_BUSY_DETAIL = "Another comparison is in progress. Try again in a moment.";

export interface AccountStatus {
  signed_in: boolean;
  paid: boolean;
  email: string | null;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface AlignmentMetadata {
  keypoints_drawing_a: number;
  keypoints_drawing_b: number;
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
  changed_pixel_count: number;
  changed_pixel_ratio: number;
}

export interface ContentMetadata {
  drawing_a_bbox: BoundingBox;
  drawing_b_bbox: BoundingBox;
  overlap_bbox: BoundingBox;
}

export interface AlignmentConfidence {
  status: "high" | "marginal" | "failed";
  message: string | null;
}

export interface OverlayMetadata {
  orange_pixels: number;
  blue_pixels: number;
  green_pixels: number;
  red_pixels: number;
}

export interface CompareMetadata {
  alignment: AlignmentMetadata;
  alignment_confidence: AlignmentConfidence;
  content: ContentMetadata;
  overlay: OverlayMetadata;
  differences: DifferenceMetadata;
}

export interface CompareResponse {
  image_path: string;
  pdf_path: string;
  metadata: CompareMetadata;
}

export interface UploadAndCompareResult {
  comparisonImageUrl: string;
  comparisonPdfUrl: string;
  metadata: CompareMetadata;
}

export async function uploadAndCompare(
  drawingA: File,
  drawingB: File,
  signal?: AbortSignal,
): Promise<UploadAndCompareResult> {
  const formData = new FormData();
  formData.append("drawing_a", drawingA);
  formData.append("drawing_b", drawingB);

  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), COMPARE_TIMEOUT_MS);

  const combinedSignal = signal
    ? mergeAbortSignals(signal, timeoutController.signal)
    : timeoutController.signal;

  try {
    const headers: Record<string, string> = {};
    const accessToken = getAuthAccessToken();
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const response = await fetch(`${API_BASE_URL}/compare`, {
      method: "POST",
      body: formData,
      headers,
      signal: combinedSignal,
    });

    if (!response.ok) {
      const errorMessage = await getErrorMessage(response);
      throw new Error(errorMessage);
    }

    const data = parseCompareResponse(await response.json());
    return {
      comparisonImageUrl: buildOutputUrl(data.image_path),
      comparisonPdfUrl: buildOutputUrl(data.pdf_path),
      metadata: data.metadata,
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Comparison timed out. Try smaller files or try again.");
    }
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error(
        "Could not reach the compare server. If you were comparing large drawings, wait a moment and try again.",
      );
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

  if (typeof data.pdf_path !== "string" || data.pdf_path.length === 0) {
    throw new Error("Comparison response is missing pdf_path.");
  }

  if (!isRecord(data.metadata)) {
    throw new Error("Comparison response is missing metadata.");
  }

  const alignment = data.metadata.alignment;
  const alignmentConfidence = data.metadata.alignment_confidence;
  const content = data.metadata.content;
  const overlay = data.metadata.overlay;
  const differences = data.metadata.differences;

  if (!isRecord(alignment) || !isRecord(differences) || !isRecord(overlay)) {
    throw new Error("Comparison metadata is incomplete.");
  }

  if (!isRecord(alignmentConfidence) || typeof alignmentConfidence.status !== "string") {
    throw new Error(
      "Comparison metadata is missing alignment confidence. Restart the API server on port 8000 so it matches the current frontend.",
    );
  }

  if (!isRecord(content) || !isRecord(content.overlap_bbox)) {
    throw new Error("Comparison metadata is missing content framing.");
  }

  if (typeof differences.changed_pixel_count !== "number") {
    throw new Error("Comparison metadata is missing difference counts.");
  }

  return {
    image_path: data.image_path,
    pdf_path: data.pdf_path,
    metadata: data.metadata,
  } as unknown as CompareResponse;
}

export function buildOutputUrl(outputPath: string): string {
  return buildImageUrl(outputPath);
}

export async function getErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) {
    return "Sign in to compare drawings.";
  }
  if (response.status === 402) {
    return `Active subscription required. Upgrade at ${UPGRADE_URL}.`;
  }
  try {
    const data = (await response.json()) as { detail?: unknown };
    const message = formatFastApiDetail(data.detail);
    if (message) {
      return message;
    }
  } catch {
    if (response.status === 503) {
      return COMPARE_BUSY_DETAIL;
    }
    return `Request failed with status ${response.status}.`;
  }

  if (response.status === 503) {
    return COMPARE_BUSY_DETAIL;
  }

  return `Request failed with status ${response.status}.`;
}

export function buildImageUrl(imagePath: string): string {
  if (/^https?:\/\//i.test(imagePath)) {
    const parsed = new URL(imagePath);
    const allowedOrigins = new Set<string>();
    const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
    const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL ?? "").replace(/\/$/, "");

    if (apiBaseUrl) {
      allowedOrigins.add(new URL(apiBaseUrl, window.location.origin).origin);
    }
    if (supabaseUrl) {
      allowedOrigins.add(new URL(supabaseUrl).origin);
    }

    if (allowedOrigins.size === 0 || !allowedOrigins.has(parsed.origin)) {
      throw new Error("Comparison image URL is not from an allowed origin.");
    }

    return imagePath;
  }

  const path = imagePath.replace(/\\/g, "/").replace(/^\/+/, "");
  return API_BASE_URL ? `${API_BASE_URL}/${path}` : `/${path}`;
}

export async function downloadFileAsBlob(fileUrl: string): Promise<Blob> {
  const response = await fetch(fileUrl);
  if (!response.ok) {
    throw new Error("Failed to download comparison file.");
  }
  return response.blob();
}

export async function downloadImageAsBlob(imageUrl: string): Promise<Blob> {
  return downloadFileAsBlob(imageUrl);
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

export function getUpgradeUrl(): string {
  return UPGRADE_URL;
}

export async function fetchAccountStatus(): Promise<AccountStatus> {
  const headers: Record<string, string> = {};
  const accessToken = getAuthAccessToken();
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}/account`, { headers });
  if (!response.ok) {
    return { signed_in: false, paid: false, email: null };
  }

  const data = (await response.json()) as AccountStatus;
  return data;
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
