import numpy as np
import pytest

from backend.app.services.alignment import AlignmentError, refine_crop_alignment, scale_homography, warp_drawing_with_homography
from backend.app.services.image_utils import build_foreground_mask, convert_to_grayscale
from backend.app.services.comparison_pipeline import _build_comparison_crops
from backend.app.services.overlay_renderer import OverlayStats, validate_overlay_stats
from backend.app.services.overlay_renderer import render_coordination_overlay
from backend.tests.fixtures.factory import bgr_array_from_image, make_drawing_a_image
from backend.tests.fixtures.mvp_assets import MVP_REVISION_PAIRS, require_mvp_assets


class TestScaleHomography:
    def test_identity_scale_preserves_homography(self) -> None:
        homography = np.array(
            [
                [1.0, 0.0, 12.0],
                [0.0, 1.0, 8.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        scaled = scale_homography(homography, 1.0)
        assert np.allclose(scaled, homography)

    def test_doubled_resolution_scales_translation(self) -> None:
        homography = np.eye(3, dtype=np.float64)
        homography[0, 2] = 10.0
        homography[1, 2] = 20.0
        scaled = scale_homography(homography, 2.0)
        assert scaled[0, 2] == pytest.approx(20.0)
        assert scaled[1, 2] == pytest.approx(40.0)


class TestWarpDrawingWithHomography:
    def test_identity_homography_preserves_image(self) -> None:
        image = bgr_array_from_image(make_drawing_a_image())
        homography = np.eye(3, dtype=np.float64)
        warped = warp_drawing_with_homography(
            image,
            homography,
            (image.shape[1], image.shape[0]),
        )
        assert warped.shape == image.shape


class TestInkDetection:
    def test_light_gray_background_still_detects_linework(self) -> None:
        image = np.full((400, 600, 3), 235, dtype=np.uint8)
        image[100:360, 120:520] = 120
        image[180:220, 140:500] = 235
        grayscale = convert_to_grayscale(image)
        mask = build_foreground_mask(grayscale)
        assert int(mask.sum() / 255) > 1000


class TestRefineCropAlignment:
    def test_identity_crop_preserves_image(self) -> None:
        image = bgr_array_from_image(make_drawing_a_image())
        refined = refine_crop_alignment(image, image)
        assert refined.shape == image.shape


class TestOverlayAgreementTolerance:
    def test_one_pixel_shift_counts_as_green_with_tolerance(self) -> None:
        image = bgr_array_from_image(make_drawing_a_image())
        shifted = np.full_like(image, 255)
        shift = 1
        height, width = image.shape[:2]
        shifted[shift:height, shift:width] = image[: height - shift, : width - shift]

        _, stats_strict = render_coordination_overlay(
            image,
            shifted,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
            include_footer=False,
        )

        import backend.app.services.overlay_renderer as overlay_renderer

        original_radius = overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS
        try:
            overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS = 0
            _, stats_no_tolerance = render_coordination_overlay(
                image,
                shifted,
                drawing_a_name="a.pdf",
                drawing_b_name="b.pdf",
                include_footer=False,
            )
        finally:
            overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS = original_radius

        assert stats_strict.green_pixels > stats_no_tolerance.green_pixels
        assert stats_strict.green_pixels > 0


class TestValidateOverlayStats:
    def test_blank_overlay_raises(self) -> None:
        stats = OverlayStats(orange_pixels=0, blue_pixels=0, green_pixels=0, red_pixels=0)
        with pytest.raises(AlignmentError):
            validate_overlay_stats(stats, crop_pixel_count=1_000_000, min_ink_pixel_ratio=0.001)

    def test_sufficient_ink_passes(self) -> None:
        stats = OverlayStats(orange_pixels=0, blue_pixels=0, green_pixels=2_000, red_pixels=0)
        validate_overlay_stats(stats, crop_pixel_count=100_000, min_ink_pixel_ratio=0.001)


class TestHiResComparisonCrops:
    def test_level3_hi_res_crops_share_dimensions(self) -> None:
        require_mvp_assets()
        from backend.app.config import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS, PDF_DPI
        from backend.app.services.alignment import (
            align_drawing_b_to_a,
            max_features_for_image,
            use_ecc_refinement_for_images,
        )
        from backend.app.services.comparison_pipeline import _pillow_to_bgr_array
        from backend.app.services.content_detection import detect_content_bbox, union_bbox
        from backend.app.services.image_limits import choose_output_dpi
        from backend.app.services.pdf_converter import load_image, load_image_with_page_info

        _, drawing_a, drawing_b = next(
            pair for pair in MVP_REVISION_PAIRS if pair[0] == "level3"
        )
        drawing_a_pil, drawing_a_page = load_image_with_page_info(drawing_a)
        drawing_a_image = _pillow_to_bgr_array(drawing_a_pil)
        drawing_b_image = _pillow_to_bgr_array(load_image(drawing_b))
        aligned_drawing_b, alignment_metadata = align_drawing_b_to_a(
            drawing_a_image,
            drawing_b_image,
            max_features=max_features_for_image(drawing_a_image),
            ecc_refinement=use_ecc_refinement_for_images(drawing_a_image, drawing_b_image),
        )
        comparison_bbox = union_bbox(
            detect_content_bbox(drawing_a_image),
            detect_content_bbox(aligned_drawing_b),
        )
        output_dpi = choose_output_dpi(
            comparison_bbox.width,
            comparison_bbox.height,
            alignment_dpi=drawing_a_page.raster_dpi,
            preferred_dpi=PDF_DPI,
            max_pixels=MAX_IMAGE_PIXELS,
            max_dimension=MAX_IMAGE_DIMENSION,
        )
        assert output_dpi > drawing_a_page.raster_dpi

        drawing_a_crop, drawing_b_crop = _build_comparison_crops(
            drawing_a,
            drawing_b,
            drawing_a_image,
            drawing_b_image,
            aligned_drawing_b,
            comparison_bbox,
            alignment_metadata=alignment_metadata,
            alignment_dpi=drawing_a_page.raster_dpi,
            output_dpi=output_dpi,
        )

        assert drawing_a_crop.shape == drawing_b_crop.shape
        assert drawing_a_crop.shape[0] > 0
        assert drawing_a_crop.shape[1] > 0
