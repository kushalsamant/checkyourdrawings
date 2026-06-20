from typing import Any

from pydantic import BaseModel


class AlignmentMetadataResponse(BaseModel):
    keypoints_drawing_a: int
    keypoints_drawing_b: int
    raw_matches: int
    good_matches: int
    inlier_matches: int
    inlier_ratio: float
    homography: list[list[float]]
    output_width: int
    output_height: int


class BoundingBoxResponse(BaseModel):
    x: int
    y: int
    width: int
    height: int


class DifferenceMetadataResponse(BaseModel):
    width: int
    height: int
    changed_pixel_count: int
    changed_pixel_ratio: float


class ContentMetadataResponse(BaseModel):
    drawing_a_bbox: BoundingBoxResponse
    drawing_b_bbox: BoundingBoxResponse
    overlap_bbox: BoundingBoxResponse
    comparison_bbox: BoundingBoxResponse


class OutputPageMetadataResponse(BaseModel):
    mode: str
    width_pt: float
    height_pt: float
    raster_dpi: int


class AlignmentConfidenceResponse(BaseModel):
    status: str
    message: str | None


class OverlayMetadataResponse(BaseModel):
    orange_pixels: int
    blue_pixels: int
    green_pixels: int
    red_pixels: int


class CompareMetadataResponse(BaseModel):
    alignment: AlignmentMetadataResponse
    alignment_confidence: AlignmentConfidenceResponse
    content: ContentMetadataResponse
    overlay: OverlayMetadataResponse
    differences: DifferenceMetadataResponse
    output_page: OutputPageMetadataResponse


class CompareResponse(BaseModel):
    image_path: str
    pdf_path: str
    metadata: CompareMetadataResponse

    @classmethod
    def from_pipeline_result(
        cls,
        image_path: str,
        pdf_path: str,
        metadata: dict[str, Any],
    ) -> "CompareResponse":
        return cls.model_validate(
            {"image_path": image_path, "pdf_path": pdf_path, "metadata": metadata}
        )


class AccountStatusResponse(BaseModel):
    signed_in: bool
    paid: bool
    email: str | None = None
