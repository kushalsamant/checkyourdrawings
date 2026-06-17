from dataclasses import dataclass
from typing import Literal, TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.config import ALIGNMENT_FAIL_INLIER_RATIO, ALIGNMENT_MARGINAL_INLIER_RATIO
from backend.app.services.image_utils import ImageArray, convert_to_grayscale


FloatMatrix: TypeAlias = NDArray[np.float64]


@dataclass(frozen=True)
class AlignmentMetadata:
    keypoints_reference: int
    keypoints_revision: int
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
    fail_inlier_ratio: float = ALIGNMENT_FAIL_INLIER_RATIO,
) -> AlignmentConfidence:
    """Classify alignment quality. Low inlier ratio warns but does not block."""
    _ = fail_inlier_ratio

    if metadata.inlier_ratio < marginal_inlier_ratio:
        return AlignmentConfidence(
            status="marginal",
            message=(
                "Alignment confidence is low. Review the comparison manually before "
                "relying on the overlay."
            ),
        )

    return AlignmentConfidence(status="high", message=None)


def align_revision_to_reference(
    reference_image: NDArray[np.generic],
    revision_image: NDArray[np.generic],
    *,
    max_features: int = 10_000,
    keep_match_ratio: float = 0.20,
    min_matches: int = 12,
    ransac_reprojection_threshold: float = 5.0,
) -> tuple[ImageArray, AlignmentMetadata]:
    """Align Revision B onto Revision A using ORB features and a RANSAC homography."""
    _validate_alignment_parameters(
        max_features=max_features,
        keep_match_ratio=keep_match_ratio,
        min_matches=min_matches,
        ransac_reprojection_threshold=ransac_reprojection_threshold,
    )

    reference_gray: ImageArray = convert_to_grayscale(reference_image)
    revision_gray: ImageArray = convert_to_grayscale(revision_image)

    orb = cv2.ORB_create(nfeatures=max_features)
    reference_keypoints, reference_descriptors = orb.detectAndCompute(reference_gray, None)
    revision_keypoints, revision_descriptors = orb.detectAndCompute(revision_gray, None)

    reference_count: int = len(reference_keypoints)
    revision_count: int = len(revision_keypoints)

    if reference_descriptors is None or revision_descriptors is None:
        raise AlignmentError(
            "Could not detect enough ORB features in one or both images for alignment."
        )

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    raw_matches = matcher.match(revision_descriptors, reference_descriptors)

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

    revision_points: FloatMatrix = np.float64(
        [revision_keypoints[match.queryIdx].pt for match in good_matches]
    ).reshape(-1, 1, 2)
    reference_points: FloatMatrix = np.float64(
        [reference_keypoints[match.trainIdx].pt for match in good_matches]
    ).reshape(-1, 1, 2)

    homography, inlier_mask = cv2.findHomography(
        revision_points,
        reference_points,
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

    output_height: int = int(reference_image.shape[0])
    output_width: int = int(reference_image.shape[1])

    aligned_image: ImageArray = cv2.warpPerspective(
        revision_image,
        homography,
        (output_width, output_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )

    metadata = AlignmentMetadata(
        keypoints_reference=reference_count,
        keypoints_revision=revision_count,
        raw_matches=len(raw_matches),
        good_matches=len(good_matches),
        inlier_matches=inlier_matches,
        inlier_ratio=inlier_matches / len(good_matches),
        homography=homography.astype(float).tolist(),
        output_width=output_width,
        output_height=output_height,
    )

    return aligned_image, metadata


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
