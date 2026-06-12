const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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
): Promise<UploadAndCompareResult> {
  const formData = new FormData();
  formData.append("revision_a", revisionA);
  formData.append("revision_b", revisionB);

  const response = await fetch(`${API_BASE_URL}/compare`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  const data = (await response.json()) as CompareResponse;

  return {
    comparisonImageUrl: buildImageUrl(data.image_path),
    metadata: data.metadata,
  };
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };

    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    return `Request failed with status ${response.status}.`;
  }

  return `Request failed with status ${response.status}.`;
}

function buildImageUrl(imagePath: string): string {
  if (/^https?:\/\//i.test(imagePath)) {
    return imagePath;
  }

  return `${API_BASE_URL}/${imagePath.replace(/\\/g, "/").replace(/^\/+/, "")}`;
}
