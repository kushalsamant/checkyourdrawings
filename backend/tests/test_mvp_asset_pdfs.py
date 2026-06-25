import gc

from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.tests.fixtures.mvp_assets import MVP_REVISION_PAIRS, require_mvp_assets

MIN_GREEN_PIXELS = 100_000
MIN_TOTAL_INK_PIXELS = 500_000
MIN_GREEN_RATIO = 0.25
MAX_CHANGED_RATIO = 0.60
MIN_INLIER_RATIO = 0.55
MIN_OUTPUT_DPI = 200


def test_all_mvp_revision_pairs_produce_usable_overlay() -> None:
    """Run each committed revision pair; gc between pairs to limit peak memory."""
    require_mvp_assets()

    for level, drawing_a, drawing_b in MVP_REVISION_PAIRS:
        gc.collect()
        result = run_comparison_pipeline(
            drawing_a,
            drawing_b,
            drawing_a.name,
            drawing_b.name,
        )

        overlay = result.metadata.overlay
        total_ink = (
            overlay.orange_pixels
            + overlay.blue_pixels
            + overlay.green_pixels
            + overlay.red_pixels
        )

        assert overlay.green_pixels >= MIN_GREEN_PIXELS, level
        assert total_ink >= MIN_TOTAL_INK_PIXELS, level
        green_ratio = overlay.green_pixels / max(1, total_ink)
        changed_ratio = (
            overlay.orange_pixels + overlay.blue_pixels + overlay.red_pixels
        ) / max(1, total_ink)
        assert green_ratio >= MIN_GREEN_RATIO, (level, green_ratio)
        assert changed_ratio <= MAX_CHANGED_RATIO, (level, changed_ratio)
        assert result.metadata.alignment.inlier_ratio >= MIN_INLIER_RATIO, level
        assert result.metadata.alignment_confidence.status == "high", level
        assert result.metadata.output_page.mode == "crop", level
        assert result.metadata.output_page.raster_dpi >= MIN_OUTPUT_DPI, level

        del result
        gc.collect()
