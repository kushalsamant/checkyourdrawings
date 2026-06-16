from typing import Any

from pydantic import BaseModel


class AlignmentMetadataResponse(BaseModel):
    keypoints_reference: int
    keypoints_revision: int
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


class DifferenceRegionResponse(BaseModel):
    kind: str
    bounding_box: BoundingBoxResponse
    area: float
    changed_pixels: int
    addition_pixels: int
    deletion_pixels: int
    confidence: float


class DifferenceMetadataResponse(BaseModel):
    width: int
    height: int
    regions: list[DifferenceRegionResponse]
    changed_pixel_count: int
    changed_pixel_ratio: float


class CompareMetadataResponse(BaseModel):
    alignment: AlignmentMetadataResponse
    differences: DifferenceMetadataResponse


class CompareResponse(BaseModel):
    image_path: str
    metadata: CompareMetadataResponse

    @classmethod
    def from_pipeline_result(cls, image_path: str, metadata: dict[str, Any]) -> "CompareResponse":
        return cls.model_validate({"image_path": image_path, "metadata": metadata})
