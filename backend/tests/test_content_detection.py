import numpy as np

from backend.app.services.content_detection import (
    BoundingBox,
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
)
from backend.app.services.alignment import align_revision_to_reference
from backend.tests.fixtures.factory import (
    bgr_array_from_image,
    make_drawing_on_canvas,
    make_padded_identical_pair,
)


class TestDetectContentBbox:
    def test_tight_bbox_around_ink_on_white_margins(self) -> None:
        image = bgr_array_from_image(make_drawing_on_canvas(600, 500, 80, 60))
        bbox = detect_content_bbox(image)

        assert bbox.x >= 60
        assert bbox.y >= 40
        assert bbox.x + bbox.width <= 520
        assert bbox.y + bbox.height <= 420

    def test_fallback_to_full_image_when_blank(self) -> None:
        image = np.full((120, 160, 3), 255, dtype=np.uint8)
        bbox = detect_content_bbox(image)
        assert bbox == BoundingBox(x=0, y=0, width=160, height=120)


class TestComputeOverlapBbox:
    def test_returns_intersection_for_overlapping_boxes(self) -> None:
        overlap = compute_overlap_bbox(
            BoundingBox(x=10, y=10, width=100, height=100),
            BoundingBox(x=60, y=60, width=100, height=100),
            min_area_ratio=0.01,
        )
        assert overlap == BoundingBox(x=60, y=60, width=50, height=50)

    def test_returns_none_for_disjoint_boxes(self) -> None:
        overlap = compute_overlap_bbox(
            BoundingBox(x=0, y=0, width=50, height=50),
            BoundingBox(x=100, y=100, width=50, height=50),
        )
        assert overlap is None


class TestCropImage:
    def test_crop_image_slices_expected_region(self) -> None:
        image = np.arange(12, dtype=np.uint8).reshape(3, 4)
        cropped = crop_image(image, BoundingBox(x=1, y=1, width=2, height=2))
        assert cropped.shape == (2, 2)
        assert cropped[0, 0] == 5


class TestMarginShiftIntegration:
    def test_identical_ink_with_different_margins_aligns_with_overlap(self) -> None:
        reference, revision = make_padded_identical_pair(
            margin_a=(40, 30, 120, 90),
            margin_b=(90, 70, 40, 30),
        )
        reference_bgr = bgr_array_from_image(reference)
        revision_bgr = bgr_array_from_image(revision)

        aligned, _ = align_revision_to_reference(reference_bgr, revision_bgr)
        reference_bbox = detect_content_bbox(reference_bgr)
        revision_bbox = detect_content_bbox(aligned)
        overlap = compute_overlap_bbox(reference_bbox, revision_bbox)
        assert overlap is not None
