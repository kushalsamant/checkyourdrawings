import pytest

from backend.app.services.content_detection import (
    BoundingBox,
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
    union_bbox,
)
from backend.app.services.alignment import align_drawing_b_to_a
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
        import numpy as np

        image = np.full((120, 160, 3), 255, dtype=np.uint8)
        bbox = detect_content_bbox(image)
        assert bbox == BoundingBox(x=0, y=0, width=160, height=120)


class TestUnionBbox:
    def test_encompasses_both_boxes(self) -> None:
        bbox_a = BoundingBox(x=10, y=20, width=100, height=80)
        bbox_b = BoundingBox(x=50, y=10, width=120, height=90)
        union = union_bbox(bbox_a, bbox_b)
        assert union == BoundingBox(x=10, y=10, width=160, height=90)

    def test_is_no_smaller_than_either_input(self) -> None:
        bbox_a = BoundingBox(x=0, y=0, width=50, height=50)
        bbox_b = BoundingBox(x=200, y=200, width=30, height=30)
        union = union_bbox(bbox_a, bbox_b)
        assert union.width >= bbox_a.width
        assert union.height >= bbox_a.height
        assert union.width >= bbox_b.width
        assert union.height >= bbox_b.height


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
        import numpy as np

        image = np.arange(12, dtype=np.uint8).reshape(3, 4)
        cropped = crop_image(image, BoundingBox(x=1, y=1, width=2, height=2))
        assert cropped.shape == (2, 2)
        assert cropped[0, 0] == 5


class TestMarginShiftIntegration:
    def test_identical_ink_with_different_margins_aligns_with_overlap(self) -> None:
        drawing_a, drawing_b = make_padded_identical_pair(
            margin_a=(40, 30, 120, 90),
            margin_b=(90, 70, 40, 30),
        )
        drawing_a_bgr = bgr_array_from_image(drawing_a)
        drawing_b_bgr = bgr_array_from_image(drawing_b)

        aligned, _ = align_drawing_b_to_a(drawing_a_bgr, drawing_b_bgr)
        drawing_a_bbox = detect_content_bbox(drawing_a_bgr)
        drawing_b_bbox = detect_content_bbox(aligned)
        overlap = compute_overlap_bbox(drawing_a_bbox, drawing_b_bbox)
        assert overlap is not None
        comparison_bbox = union_bbox(drawing_a_bbox, drawing_b_bbox)
        assert comparison_bbox.width >= drawing_a_bbox.width
        assert comparison_bbox.height >= drawing_a_bbox.height
