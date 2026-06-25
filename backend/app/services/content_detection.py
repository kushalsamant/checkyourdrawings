from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.config import CONTENT_BBOX_PADDING_RATIO, MIN_OVERLAP_AREA_RATIO
from backend.app.services.image_utils import ImageArray, build_framing_mask, convert_to_grayscale

_MAX_PADDING_PX = 64


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


def detect_content_bbox(
    image: NDArray[np.generic],
    *,
    padding_ratio: float = CONTENT_BBOX_PADDING_RATIO,
) -> BoundingBox:
    """Detect a bounding box around drawing ink on a page."""
    if image.size == 0:
        raise ValueError("image must not be empty.")

    height, width = image.shape[:2]
    grayscale: ImageArray = convert_to_grayscale(image)
    foreground_mask: ImageArray = build_framing_mask(grayscale)

    ink_pixels = cv2.findNonZero(foreground_mask)
    if ink_pixels is None:
        return BoundingBox(x=0, y=0, width=width, height=height)

    x, y, bbox_width, bbox_height = cv2.boundingRect(ink_pixels)
    padding = min(_MAX_PADDING_PX, int(min(width, height) * padding_ratio))

    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(width, x + bbox_width + padding)
    bottom = min(height, y + bbox_height + padding)

    return BoundingBox(
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
    )


def compute_overlap_bbox(
    bbox_a: BoundingBox,
    bbox_b: BoundingBox,
    *,
    min_area_ratio: float = MIN_OVERLAP_AREA_RATIO,
) -> BoundingBox | None:
    """Return the intersection of two bounding boxes when overlap is large enough."""
    intersection = _intersect_bboxes(bbox_a, bbox_b)
    if intersection is None:
        return None

    overlap_area = intersection.width * intersection.height
    union_area = _union_area(bbox_a, bbox_b)
    if union_area <= 0:
        return None

    if overlap_area / union_area < min_area_ratio:
        return None

    return intersection


def _intersect_bboxes(bbox_a: BoundingBox, bbox_b: BoundingBox) -> BoundingBox | None:
    left = max(bbox_a.x, bbox_b.x)
    top = max(bbox_a.y, bbox_b.y)
    right = min(bbox_a.x + bbox_a.width, bbox_b.x + bbox_b.width)
    bottom = min(bbox_a.y + bbox_a.height, bbox_b.y + bbox_b.height)

    if right <= left or bottom <= top:
        return None

    return BoundingBox(
        x=left,
        y=top,
        width=right - left,
        height=bottom - top,
    )


def union_bbox(bbox_a: BoundingBox, bbox_b: BoundingBox) -> BoundingBox:
    """Return the smallest axis-aligned box containing both inputs."""
    left = min(bbox_a.x, bbox_b.x)
    top = min(bbox_a.y, bbox_b.y)
    right = max(bbox_a.x + bbox_a.width, bbox_b.x + bbox_b.width)
    bottom = max(bbox_a.y + bbox_a.height, bbox_b.y + bbox_b.height)
    return BoundingBox(x=left, y=top, width=right - left, height=bottom - top)


def _union_area(bbox_a: BoundingBox, bbox_b: BoundingBox) -> int:
    intersection = _intersect_bboxes(bbox_a, bbox_b)
    area_a = bbox_a.width * bbox_a.height
    area_b = bbox_b.width * bbox_b.height
    if intersection is None:
        return area_a + area_b
    return area_a + area_b - (intersection.width * intersection.height)


def scale_bbox(bbox: BoundingBox, scale: float) -> BoundingBox:
    """Scale a bounding box between raster resolutions."""
    if scale <= 0:
        raise ValueError("scale must be greater than zero.")

    return BoundingBox(
        x=int(round(bbox.x * scale)),
        y=int(round(bbox.y * scale)),
        width=int(round(bbox.width * scale)),
        height=int(round(bbox.height * scale)),
    )


def crop_image(image: NDArray[np.generic], bbox: BoundingBox) -> NDArray[np.generic]:
    """Crop an image to a bounding box."""
    if image.size == 0:
        raise ValueError("image must not be empty.")

    y_end = bbox.y + bbox.height
    x_end = bbox.x + bbox.width
    return image[bbox.y : y_end, bbox.x : x_end].copy()
