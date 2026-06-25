from dataclasses import dataclass
from typing import Literal, TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.config import (
    ALIGNMENT_ECC_REFINEMENT,
    ALIGNMENT_LARGE_IMAGE_MAX_FEATURES,
    ALIGNMENT_LARGE_IMAGE_PIXELS,
    ALIGNMENT_MARGINAL_INLIER_RATIO,
    COMPARE_DISABLE_ECC_ABOVE_PIXELS,
    CROP_ECC_MAX_PIXELS,
)
from backend.app.services.image_utils import ImageArray, convert_to_grayscale


FloatMatrix: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True)
class AlignmentMetadata:
    keypoints_drawing_a: int
    keypoints_drawing_b: int
    raw_matches: int
    good_matches: int
    inlier_matches: int
    inlier_ratio: float
    homography: list[list[float]]
    output_width: int
    output_height: int


class AlignmentError(Exception):
    """Raised when image alignment cannot be computed reliably."""


@dataclass(frozen=True)
class AlignmentConfidence:
    status: Literal["high", "marginal", "failed"]
    message: str | None


def evaluate_alignment_confidence(
    metadata: AlignmentMetadata,
    *,
    marginal_inlier_ratio: float = ALIGNMENT_MARGINAL_INLIER_RATIO,
) -> AlignmentConfidence:
    """Classify alignment quality. Low inlier ratio warns but does not block."""
    if metadata.inlier_ratio < marginal_inlier_ratio:
        return AlignmentConfidence(
            status="marginal",
            message=(
                "Alignment confidence is low. Review the overlay manually."
            ),
        )

    return AlignmentConfidence(status="high", message=None)


def max_features_for_image(
    image: NDArray[np.generic],
    *,
    default_max_features: int = 10_000,
    large_image_pixels: int = ALIGNMENT_LARGE_IMAGE_PIXELS,
    large_image_max_features: int = ALIGNMENT_LARGE_IMAGE_MAX_FEATURES,
) -> int:
    """Use fewer ORB features on large rasters to reduce peak memory."""
    height, width = image.shape[:2]
    if height * width > large_image_pixels:
        return large_image_max_features
    return default_max_features


def use_ecc_refinement_for_images(
    drawing_a_image: NDArray[np.generic],
    drawing_b_image: NDArray[np.generic],
    *,
    ecc_refinement_enabled: bool = ALIGNMENT_ECC_REFINEMENT,
    disable_above_pixels: int = COMPARE_DISABLE_ECC_ABOVE_PIXELS,
) -> bool:
    if not ecc_refinement_enabled:
        return False

    drawing_a_pixels = int(drawing_a_image.shape[0] * drawing_a_image.shape[1])
    drawing_b_pixels = int(drawing_b_image.shape[0] * drawing_b_image.shape[1])
    return max(drawing_a_pixels, drawing_b_pixels) <= disable_above_pixels


def scale_homography(homography: FloatMatrix, scale: float) -> FloatMatrix:
    """Scale a homography when moving between raster resolutions."""
    if abs(scale - 1.0) < 1e-9:
        return homography.astype(np.float64, copy=False)

    inverse_scale = 1.0 / scale
    normalize = np.array(
        [
            [inverse_scale, 0.0, 0.0],
            [0.0, inverse_scale, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    upscale = np.array(
        [
            [scale, 0.0, 0.0],
            [0.0, scale, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    return upscale @ homography.astype(np.float64) @ normalize


def warp_drawing_with_homography(
    drawing_image: NDArray[np.generic],
    homography: FloatMatrix,
    output_size: tuple[int, int],
) -> ImageArray:
    """Warp a drawing image with a homography onto a target canvas size."""
    output_width, output_height = output_size
    return cv2.warpPerspective(
        drawing_image,
        homography,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def align_drawing_b_to_a(
    drawing_a_image: NDArray[np.generic],
    drawing_b_image: NDArray[np.generic],
    *,
    max_features: int = 10_000,
    keep_match_ratio: float = 0.20,
    min_matches: int = 12,
    ransac_reprojection_threshold: float = 5.0,
    ecc_refinement: bool = ALIGNMENT_ECC_REFINEMENT,
) -> tuple[ImageArray, AlignmentMetadata]:
    """Align Drawing B onto Drawing A using ORB features and a RANSAC homography."""
    _validate_alignment_parameters(
        max_features=max_features,
        keep_match_ratio=keep_match_ratio,
        min_matches=min_matches,
        ransac_reprojection_threshold=ransac_reprojection_threshold,
    )

    drawing_a_gray: ImageArray = convert_to_grayscale(drawing_a_image)
    drawing_b_gray: ImageArray = convert_to_grayscale(drawing_b_image)

    orb = cv2.ORB_create(nfeatures=max_features)
    drawing_a_keypoints, drawing_a_descriptors = orb.detectAndCompute(drawing_a_gray, None)
    drawing_b_keypoints, drawing_b_descriptors = orb.detectAndCompute(drawing_b_gray, None)

    drawing_a_count: int = len(drawing_a_keypoints)
    drawing_b_count: int = len(drawing_b_keypoints)

    if drawing_a_descriptors is None or drawing_b_descriptors is None:
        raise AlignmentError(
            "Could not detect enough ORB features in one or both images for alignment."
        )

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    raw_matches = matcher.match(drawing_b_descriptors, drawing_a_descriptors)

    if len(raw_matches) < min_matches:
        raise AlignmentError(
            f"Not enough feature matches for alignment: found {len(raw_matches)}, "
            f"required at least {min_matches}."
        )

    raw_matches = sorted(raw_matches, key=lambda match: match.distance)
    keep_count: int = max(min_matches, int(len(raw_matches) * keep_match_ratio))
    good_matches = raw_matches[:keep_count]

    if len(good_matches) < min_matches:
        raise AlignmentError(
            f"Not enough high-quality matches for alignment: found {len(good_matches)}, "
            f"required at least {min_matches}."
        )

    drawing_b_points: FloatMatrix = np.float64(
        [drawing_b_keypoints[match.queryIdx].pt for match in good_matches]
    ).reshape(-1, 1, 2)
    drawing_a_points: FloatMatrix = np.float64(
        [drawing_a_keypoints[match.trainIdx].pt for match in good_matches]
    ).reshape(-1, 1, 2)

    homography, inlier_mask = cv2.findHomography(
        drawing_b_points,
        drawing_a_points,
        cv2.RANSAC,
        ransac_reprojection_threshold,
    )

    if homography is None or inlier_mask is None:
        raise AlignmentError("Could not compute a reliable homography for alignment.")

    inlier_matches: int = int(inlier_mask.sum())

    if inlier_matches < min_matches:
        raise AlignmentError(
            f"Homography is unreliable: found {inlier_matches} inlier matches, "
            f"required at least {min_matches}."
        )

    output_height: int = int(drawing_a_image.shape[0])
    output_width: int = int(drawing_a_image.shape[1])

    aligned_image: ImageArray = cv2.warpPerspective(
        drawing_b_image,
        homography,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )

    if ecc_refinement:
        aligned_image = refine_alignment_with_ecc(drawing_a_image, aligned_image)

    metadata = AlignmentMetadata(
        keypoints_drawing_a=drawing_a_count,
        keypoints_drawing_b=drawing_b_count,
        raw_matches=len(raw_matches),
        good_matches=len(good_matches),
        inlier_matches=inlier_matches,
        inlier_ratio=inlier_matches / len(good_matches),
        homography=homography.astype(float).tolist(),
        output_width=output_width,
        output_height=output_height,
    )

    return aligned_image, metadata


def refine_alignment_with_ecc(
    drawing_a_image: NDArray[np.generic],
    aligned_image: NDArray[np.generic],
) -> ImageArray:
    """Refine aligned Drawing B with sub-pixel ECC on grayscale ink."""
    drawing_a_gray = convert_to_grayscale(drawing_a_image).astype(np.float32) / 255.0
    aligned_gray = convert_to_grayscale(aligned_image).astype(np.float32) / 255.0

    if drawing_a_gray.shape != aligned_gray.shape:
        return aligned_image

    warp_matrix = _find_ecc_warp_matrix(drawing_a_gray, aligned_gray)
    if warp_matrix is None:
        return aligned_image

    height, width = drawing_a_image.shape[:2]
    return cv2.warpAffine(
        aligned_image,
        warp_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def refine_crop_alignment(
    drawing_a_image: NDArray[np.generic],
    aligned_image: NDArray[np.generic],
    *,
    max_ecc_pixels: int = CROP_ECC_MAX_PIXELS,
) -> ImageArray:
    """Refine hi-res comparison crops; downscales for ECC when crops are large."""
    if drawing_a_image.shape[:2] != aligned_image.shape[:2]:
        return aligned_image

    height, width = drawing_a_image.shape[:2]
    pixel_count = height * width
    if pixel_count <= max_ecc_pixels:
        return refine_alignment_with_ecc(drawing_a_image, aligned_image)

    scale = (max_ecc_pixels / pixel_count) ** 0.5
    new_width = max(64, int(round(width * scale)))
    new_height = max(64, int(round(height * scale)))

    drawing_a_small = cv2.resize(
        drawing_a_image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )
    aligned_small = cv2.resize(
        aligned_image,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )

    drawing_a_gray = convert_to_grayscale(drawing_a_small).astype(np.float32) / 255.0
    aligned_gray = convert_to_grayscale(aligned_small).astype(np.float32) / 255.0
    warp_matrix = _find_ecc_warp_matrix(drawing_a_gray, aligned_gray)
    if warp_matrix is None:
        return aligned_image

    coord_scale = width / new_width
    warp_matrix[0, 2] *= coord_scale
    warp_matrix[1, 2] *= coord_scale

    return cv2.warpAffine(
        aligned_image,
        warp_matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def _find_ecc_warp_matrix(
    drawing_a_gray: NDArray[np.float32],
    aligned_gray: NDArray[np.float32],
) -> NDArray[np.float32] | None:
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)

    try:
        _, warp_matrix = cv2.findTransformECC(
            drawing_a_gray,
            aligned_gray,
            warp_matrix,
            cv2.MOTION_EUCLIDEAN,
            criteria,
            inputMask=None,
            gaussFiltSize=5,
        )
    except cv2.error:
        return None

    return warp_matrix


def _validate_alignment_parameters(
    *,
    max_features: int,
    keep_match_ratio: float,
    min_matches: int,
    ransac_reprojection_threshold: float,
) -> None:
    if max_features <= 0:
        raise ValueError("max_features must be greater than zero.")

    if not 0 < keep_match_ratio <= 1:
        raise ValueError("keep_match_ratio must be greater than 0 and no more than 1.")

    if min_matches < 4:
        raise ValueError("min_matches must be at least 4 to compute a homography.")

    if ransac_reprojection_threshold <= 0:
        raise ValueError("ransac_reprojection_threshold must be greater than zero.")
