import { ANON_SESSION_HEADER, getAnonSessionId } from "../lib/anon-session";
import { clearAuthAccessToken, getAuthAccessToken } from "../lib/auth-provider";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const COMPARE_TIMEOUT_MS = 5 * 60 * 1000;
const COMPARE_POLL_INTERVAL_MS = 1500;
const COMPARE_BUSY_DETAIL = "Another comparison is running. Wait, then try again.";
export const SIGN_IN_TO_CONTINUE_MESSAGE = "Sign in to continue.";

export class SignInRequiredError extends Error {
  constructor(message: string = SIGN_IN_TO_CONTINUE_MESSAGE) {
    super(message);
    this.name = "SignInRequiredError";
  }
}

export interface AllowanceStatus {
  tier: "anonymous" | "free" | "pro" | string;
  remaining: number | null;
  total: number | null;
  requires_sign_in: boolean;
}

export interface CompareJobCreatedResponse {
  job_id: string;
}

export interface CompareJobStatusResponse {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed" | string;
  stage?: string | null;
  result: CompareResponse | null;
  error_message: string | null;
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

export function buildCompareRequestHeaders(options?: {
  preferAnonymous?: boolean;
}): Record<string, string> {
  const headers: Record<string, string> = {};
  const accessToken = options?.preferAnonymous ? null : getAuthAccessToken();
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  } else {
    headers[ANON_SESSION_HEADER] = getAnonSessionId();
  }
  return headers;
}

export async function fetchAllowance(
  isSignedIn: boolean,
  signal?: AbortSignal,
): Promise<AllowanceStatus | null> {
  const requestAllowance = async (signedIn: boolean): Promise<Response> =>
    fetch(`${API_BASE_URL}/allowance`, {
      headers: buildCompareRequestHeaders({ preferAnonymous: !signedIn }),
      signal,
    });

  try {
    let response = await requestAllowance(isSignedIn);

    if (response.status === 401 && isSignedIn) {
      clearAuthAccessToken();
      response = await requestAllowance(false);
    }

    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AllowanceStatus;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return null;
    }
    return null;
  }
}

export async function uploadAndCompare(
  drawingA: File,
  drawingB: File,
  signal?: AbortSignal,
  onStage?: (stage: string | null) => void,
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
    const headers = buildCompareRequestHeaders();

    const response = await fetch(`${API_BASE_URL}/compare`, {
      method: "POST",
      body: formData,
      headers,
      signal: combinedSignal,
    });

    if (!response.ok) {
      if (response.status === 401) {
        clearAuthAccessToken();
      }
      const errorMessage = await getErrorMessage(response);
      if (response.status === 401 && errorMessage === SIGN_IN_TO_CONTINUE_MESSAGE) {
        throw new SignInRequiredError(errorMessage);
      }
      throw new Error(errorMessage);
    }

    if (response.status === 202) {
      const queued = (await response.json()) as CompareJobCreatedResponse;
      if (!queued.job_id) {
        throw new Error("Comparison response is missing job_id.");
      }
      const completed = await pollCompareJob(queued.job_id, combinedSignal, onStage);
      const data = parseCompareResponse(completed);
      return {
        comparisonImageUrl: buildOutputUrl(data.image_path),
        comparisonPdfUrl: buildOutputUrl(data.pdf_path),
        metadata: data.metadata,
      };
    }

    const data = parseCompareResponse(await response.json());
    return {
      comparisonImageUrl: buildOutputUrl(data.image_path),
      comparisonPdfUrl: buildOutputUrl(data.pdf_path),
      metadata: data.metadata,
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Comparison timed out. Try again or use smaller files.");
    }
    if (error instanceof TypeError && error.message === "Failed to fetch") {
      throw new Error(
        "Could not reach the server. Wait a moment, then try again.",
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
    return "Sign in to continue.";
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
    const platformApiUrl = (import.meta.env.VITE_PLATFORM_API_URL ?? "").replace(/\/$/, "");
    const bunnyCdnHost = (import.meta.env.VITE_BUNNY_CDN_HOSTNAME ?? "").replace(/\/$/, "");

    if (apiBaseUrl) {
      allowedOrigins.add(new URL(apiBaseUrl, window.location.origin).origin);
    }
    if (platformApiUrl) {
      allowedOrigins.add(new URL(platformApiUrl, window.location.origin).origin);
    }
    if (bunnyCdnHost) {
      allowedOrigins.add(new URL(`https://${bunnyCdnHost}`).origin);
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

async function pollCompareJob(
  jobId: string,
  signal: AbortSignal,
  onStage?: (stage: string | null) => void,
): Promise<CompareResponse> {
  const headers = buildCompareRequestHeaders();

  while (true) {
    if (signal.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`, { headers, signal });
    if (!response.ok) {
      if (response.status === 401) {
        clearAuthAccessToken();
      }
      throw new Error(await getErrorMessage(response));
    }

    const payload = (await response.json()) as CompareJobStatusResponse;
    onStage?.(payload.stage ?? null);
    if (payload.status === "completed" && payload.result) {
      return payload.result;
    }
    if (payload.status === "failed") {
      throw new Error(payload.error_message ?? "Comparison failed. Try again.");
    }

    await new Promise((resolve) => window.setTimeout(resolve, COMPARE_POLL_INTERVAL_MS));
  }
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
