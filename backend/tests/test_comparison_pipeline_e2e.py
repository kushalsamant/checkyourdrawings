from pathlib import Path

import pytest

from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.tests.fixtures.pdf_factory import PdfFixturePair, write_pdf_fixture_pair

MIN_OVERLAY_INK_PIXELS = 500


class TestComparisonPipelineEndToEnd:
    def test_identical_pair_produces_green_ink(self, tmp_path: Path) -> None:
        drawing_a, drawing_b = write_pdf_fixture_pair(tmp_path, PdfFixturePair.IDENTICAL)
        result = run_comparison_pipeline(drawing_a, drawing_b, drawing_a.name, drawing_b.name)

        assert result.metadata.overlay.green_pixels >= MIN_OVERLAY_INK_PIXELS
        assert result.metadata.output_page.mode == "crop"

    def test_light_linework_pair_detects_ink(self, tmp_path: Path) -> None:
        drawing_a, drawing_b = write_pdf_fixture_pair(tmp_path, PdfFixturePair.LIGHT_LINEWORK)
        result = run_comparison_pipeline(drawing_a, drawing_b, drawing_a.name, drawing_b.name)

        overlay = result.metadata.overlay
        total_ink = (
            overlay.orange_pixels
            + overlay.blue_pixels
            + overlay.green_pixels
            + overlay.red_pixels
        )
        assert total_ink >= MIN_OVERLAY_INK_PIXELS

    def test_margin_shift_pair_aligns_with_overlap(self, tmp_path: Path) -> None:
        drawing_a, drawing_b = write_pdf_fixture_pair(tmp_path, PdfFixturePair.MARGIN_SHIFT)
        result = run_comparison_pipeline(drawing_a, drawing_b, drawing_a.name, drawing_b.name)

        overlap = result.metadata.content.overlap_bbox
        assert overlap.width > 0
        assert overlap.height > 0
        assert result.metadata.overlay.green_pixels >= MIN_OVERLAY_INK_PIXELS

    def test_modified_pair_reports_changes(self, tmp_path: Path) -> None:
        drawing_a, drawing_b = write_pdf_fixture_pair(tmp_path, PdfFixturePair.MODIFIED)
        result = run_comparison_pipeline(drawing_a, drawing_b, drawing_a.name, drawing_b.name)

        overlay = result.metadata.overlay
        changed_pixels = overlay.orange_pixels + overlay.blue_pixels + overlay.red_pixels
        assert changed_pixels > 0
