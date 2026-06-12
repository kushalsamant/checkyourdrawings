from dataclasses import dataclass
from typing import Literal, TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.services.image_utils import ImageArray, convert_to_grayscale


DifferenceKind: TypeAlias = Literal["addition", "deletion", "modification"]


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DifferenceRegion:
    kind: DifferenceKind
    bounding_box: BoundingBox
    area: float
    changed_pixels: int
    addition_pixels: int
    deletion_pixels: int
    confidence: float


@dataclass(frozen=True)
class DifferenceResult:
    width: int
    height: int
    regions: list[DifferenceRegion]
    changed_pixel_count: int
    changed_pixel_ratio: float


class DifferenceError(Exception):
    """Raised when aligned images cannot be compared."""


def detect_differences(
    reference_image: NDArray[np.generic],
    revision_image: NDArray[np.generic],
    *,
    min_region_area: float = 40.0,
    blur_kernel_size: int = 5,
    morphology_kernel_size: int = 3,
    foreground_threshold: int | None = None,
    difference_threshold: int = 25,
    classification_ratio: float = 1.35,
) -> DifferenceResult:
    """Detect meaningful drawing differences between aligned reference and revision images."""
    _validate_inputs(reference_image, revision_image)
    _validate_parameters(
        min_region_area=min_region_area,
        blur_kernel_size=blur_kernel_size,
        morphology_kernel_size=morphology_kernel_size,
        difference_threshold=difference_threshold,
        classification_ratio=classification_ratio,
    )

    reference_gray: ImageArray = _preprocess_for_difference(
        convert_to_grayscale(reference_image),
        blur_kernel_size=blur_kernel_size,
    )
    revision_gray: ImageArray = _preprocess_for_difference(
        convert_to_grayscale(revision_image),
        blur_kernel_size=blur_kernel_size,
    )

    difference_mask: ImageArray = _build_difference_mask(
        reference_gray,
        revision_gray,
        difference_threshold=difference_threshold,
        morphology_kernel_size=morphology_kernel_size,
    )

    reference_foreground: ImageArray = _build_foreground_mask(
        reference_gray,
        threshold=foreground_threshold,
        morphology_kernel_size=morphology_kernel_size,
    )
    revision_foreground: ImageArray = _build_foreground_mask(
        revision_gray,
        threshold=foreground_threshold,
        morphology_kernel_size=morphology_kernel_size,
    )

    contours, _ = cv2.findContours(
        difference_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    regions: list[DifferenceRegion] = []

    for contour in contours:
        area: float = float(cv2.contourArea(contour))
        if area < min_region_area:
            continue

        x, y, width, height = cv2.boundingRect(contour)
        region_slice = np.s_[y : y + height, x : x + width]

        changed_region: ImageArray = difference_mask[region_slice]
        reference_region: ImageArray = reference_foreground[region_slice]
        revision_region: ImageArray = revision_foreground[region_slice]

        addition_mask: ImageArray = cv2.bitwise_and(
            revision_region,
            cv2.bitwise_not(reference_region),
        )
        deletion_mask: ImageArray = cv2.bitwise_and(
            reference_region,
            cv2.bitwise_not(revision_region),
        )

        changed_pixels: int = int(cv2.countNonZero(changed_region))
        addition_pixels: int = int(cv2.countNonZero(addition_mask))
        deletion_pixels: int = int(cv2.countNonZero(deletion_mask))

        if changed_pixels == 0:
            continue

        kind: DifferenceKind = _classify_region(
            addition_pixels=addition_pixels,
            deletion_pixels=deletion_pixels,
            classification_ratio=classification_ratio,
        )

        regions.append(
            DifferenceRegion(
                kind=kind,
                bounding_box=BoundingBox(
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                ),
                area=area,
                changed_pixels=changed_pixels,
                addition_pixels=addition_pixels,
                deletion_pixels=deletion_pixels,
                confidence=_calculate_confidence(
                    kind=kind,
                    addition_pixels=addition_pixels,
                    deletion_pixels=deletion_pixels,
                    changed_pixels=changed_pixels,
                ),
            )
        )

    regions.sort(
        key=lambda region: (
            region.bounding_box.y,
            region.bounding_box.x,
            -region.changed_pixels,
        )
    )

    height: int = int(reference_image.shape[0])
    width: int = int(reference_image.shape[1])
    changed_pixel_count: int = int(cv2.countNonZero(difference_mask))

    return DifferenceResult(
        width=width,
        height=height,
        regions=regions,
        changed_pixel_count=changed_pixel_count,
        changed_pixel_ratio=changed_pixel_count / float(width * height),
    )


def create_visual_difference_mask(
    reference_image: NDArray[np.generic],
    revision_image: NDArray[np.generic],
    *,
    difference_threshold: int = 25,
    blur_kernel_size: int = 5,
    morphology_kernel_size: int = 3,
) -> ImageArray:
    """Return a cleaned binary mask of meaningful pixel differences."""
    _validate_inputs(reference_image, revision_image)

    reference_gray: ImageArray = _preprocess_for_difference(
        convert_to_grayscale(reference_image),
        blur_kernel_size=blur_kernel_size,
    )
    revision_gray: ImageArray = _preprocess_for_difference(
        convert_to_grayscale(revision_image),
        blur_kernel_size=blur_kernel_size,
    )

    return _build_difference_mask(
        reference_gray,
        revision_gray,
        difference_threshold=difference_threshold,
        morphology_kernel_size=morphology_kernel_size,
    )


def _preprocess_for_difference(
    image: ImageArray,
    *,
    blur_kernel_size: int,
) -> ImageArray:
    if blur_kernel_size <= 1:
        return image.copy()

    return cv2.GaussianBlur(
        image,
        (blur_kernel_size, blur_kernel_size),
        sigmaX=0,
    )


def _build_difference_mask(
    reference_gray: ImageArray,
    revision_gray: ImageArray,
    *,
    difference_threshold: int,
    morphology_kernel_size: int,
) -> ImageArray:
    pixel_difference: ImageArray = cv2.absdiff(reference_gray, revision_gray)
    _, difference_mask = cv2.threshold(
        pixel_difference,
        difference_threshold,
        255,
        cv2.THRESH_BINARY,
    )

    return _clean_mask(
        difference_mask,
        morphology_kernel_size=morphology_kernel_size,
    )


def _build_foreground_mask(
    grayscale_image: ImageArray,
    *,
    threshold: int | None,
    morphology_kernel_size: int,
) -> ImageArray:
    if threshold is None:
        _, mask = cv2.threshold(
            grayscale_image,
            0,
            255,
            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
        )
    else:
        if not 0 <= threshold <= 255:
            raise ValueError("foreground_threshold must be between 0 and 255.")

        _, mask = cv2.threshold(
            grayscale_image,
            threshold,
            255,
            cv2.THRESH_BINARY_INV,
        )

    return _clean_mask(mask, morphology_kernel_size=morphology_kernel_size)


def _clean_mask(mask: ImageArray, *, morphology_kernel_size: int) -> ImageArray:
    kernel: ImageArray = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (morphology_kernel_size, morphology_kernel_size),
    )

    opened: ImageArray = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    closed: ImageArray = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)
    return closed


def _classify_region(
    *,
    addition_pixels: int,
    deletion_pixels: int,
    classification_ratio: float,
) -> DifferenceKind:
    if addition_pixels > deletion_pixels * classification_ratio:
        return "addition"

    if deletion_pixels > addition_pixels * classification_ratio:
        return "deletion"

    return "modification"


def _calculate_confidence(
    *,
    kind: DifferenceKind,
    addition_pixels: int,
    deletion_pixels: int,
    changed_pixels: int,
) -> float:
    if changed_pixels <= 0:
        return 0.0

    if kind == "addition":
        return min(1.0, addition_pixels / changed_pixels)

    if kind == "deletion":
        return min(1.0, deletion_pixels / changed_pixels)

    balanced_pixels: int = min(addition_pixels, deletion_pixels) * 2
    return min(1.0, balanced_pixels / changed_pixels)


def _validate_inputs(
    reference_image: NDArray[np.generic],
    revision_image: NDArray[np.generic],
) -> None:
    if reference_image.size == 0:
        raise DifferenceError("reference_image must not be empty.")

    if revision_image.size == 0:
        raise DifferenceError("revision_image must not be empty.")

    if reference_image.shape[:2] != revision_image.shape[:2]:
        raise DifferenceError(
            "Images must be aligned and have matching dimensions before differencing."
        )


def _validate_parameters(
    *,
    min_region_area: float,
    blur_kernel_size: int,
    morphology_kernel_size: int,
    difference_threshold: int,
    classification_ratio: float,
) -> None:
    if min_region_area <= 0:
        raise ValueError("min_region_area must be greater than zero.")

    if blur_kernel_size < 1 or blur_kernel_size % 2 == 0:
        raise ValueError("blur_kernel_size must be a positive odd integer.")

    if morphology_kernel_size < 1 or morphology_kernel_size % 2 == 0:
        raise ValueError("morphology_kernel_size must be a positive odd integer.")

    if not 0 <= difference_threshold <= 255:
        raise ValueError("difference_threshold must be between 0 and 255.")

    if classification_ratio <= 1:
        raise ValueError("classification_ratio must be greater than 1.")
