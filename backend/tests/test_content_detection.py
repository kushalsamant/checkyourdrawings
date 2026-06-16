import numpy as np

from backend.app.services.content_detection import (
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
    translate_difference_result,
)
from backend.app.services.differencer import BoundingBox, DifferenceRegion, DifferenceResult
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

    def test_comparison_bbox_includes_ink_from_both_revisions(self) -> None:
        from backend.app.services.content_detection import compute_comparison_bbox

        comparison = compute_comparison_bbox(
            BoundingBox(x=0, y=0, width=200, height=200),
            BoundingBox(x=50, y=50, width=120, height=120),
            image_width=300,
            image_height=250,
            min_area_ratio=0.01,
        )
        assert comparison == BoundingBox(x=0, y=0, width=200, height=200)


class TestCropAndTranslate:
    def test_crop_image_slices_expected_region(self) -> None:
        image = np.arange(12, dtype=np.uint8).reshape(3, 4)
        cropped = crop_image(image, BoundingBox(x=1, y=1, width=2, height=2))
        assert cropped.shape == (2, 2)
        assert cropped[0, 0] == 5

    def test_translate_difference_result_shifts_region_boxes(self) -> None:
        result = DifferenceResult(
            width=100,
            height=80,
            regions=[
                DifferenceRegion(
                    kind="addition",
                    bounding_box=BoundingBox(x=5, y=10, width=20, height=15),
                    area=100.0,
                    changed_pixels=50,
                    addition_pixels=50,
                    deletion_pixels=0,
                    confidence=1.0,
                )
            ],
            changed_pixel_count=50,
            changed_pixel_ratio=0.01,
        )

        translated = translate_difference_result(result, 30, 40)
        assert translated.regions[0].bounding_box == BoundingBox(
            x=35,
            y=50,
            width=20,
            height=15,
        )


class TestMarginShiftIntegration:
    def test_identical_ink_with_different_margins_has_near_zero_changes(self) -> None:
        reference, revision = make_padded_identical_pair(
            margin_a=(40, 30, 120, 90),
            margin_b=(90, 70, 40, 30),
        )
        reference_bgr = bgr_array_from_image(reference)
        revision_bgr = bgr_array_from_image(revision)

        from backend.app.services.alignment import align_revision_to_reference
        from backend.app.services.differencer import detect_differences

        aligned, _ = align_revision_to_reference(reference_bgr, revision_bgr)
        reference_bbox = detect_content_bbox(reference_bgr)
        revision_bbox = detect_content_bbox(aligned)
        overlap = compute_overlap_bbox(reference_bbox, revision_bbox)
        assert overlap is not None

        difference_result = detect_differences(
            crop_image(reference_bgr, overlap),
            crop_image(aligned, overlap),
        )
        assert difference_result.changed_pixel_count <= 100
