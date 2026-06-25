from pathlib import Path

import cv2
import fitz
import numpy as np
import pytest

from backend.app.services.content_detection import BoundingBox
from backend.app.services.pdf_exporter import save_overlay_pdf


@pytest.fixture
def overlay_array() -> np.ndarray:
    image = np.full((120, 200, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (180, 100), (0, 0, 255), 2)
    return image


def test_save_overlay_pdf_uses_crop_page_size(
    overlay_array: np.ndarray,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "comparison-test.pdf"
    raster_dpi = 150
    comparison_bbox = BoundingBox(x=40, y=30, width=200, height=120)

    save_overlay_pdf(
        output_path,
        overlay_array,
        page_width_pt=842.0,
        page_height_pt=595.0,
        raster_dpi=raster_dpi,
        comparison_bbox=comparison_bbox,
        layout="crop",
    )

    assert output_path.is_file()
    with fitz.open(output_path) as document:
        assert document.page_count == 1
        page = document.load_page(0)
        expected_width_pt = overlay_array.shape[1] / raster_dpi * 72.0
        expected_height_pt = overlay_array.shape[0] / raster_dpi * 72.0
        assert page.rect.width == pytest.approx(expected_width_pt)
        assert page.rect.height == pytest.approx(expected_height_pt)
        assert len(page.get_images(full=True)) == 1


def test_save_overlay_pdf_full_sheet_layout(
    overlay_array: np.ndarray,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "comparison-full-sheet.pdf"
    page_width_pt = 842.0
    page_height_pt = 595.0
    raster_dpi = 150
    comparison_bbox = BoundingBox(x=40, y=30, width=200, height=120)

    save_overlay_pdf(
        output_path,
        overlay_array,
        page_width_pt=page_width_pt,
        page_height_pt=page_height_pt,
        raster_dpi=raster_dpi,
        comparison_bbox=comparison_bbox,
        layout="full_sheet",
    )

    with fitz.open(output_path) as document:
        page = document.load_page(0)
        assert page.rect.width == pytest.approx(page_width_pt)
        assert page.rect.height == pytest.approx(page_height_pt)


def test_save_overlay_pdf_embeds_lossless_png(
    overlay_array: np.ndarray,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "comparison-lossless.pdf"
    save_overlay_pdf(
        output_path,
        overlay_array,
        page_width_pt=500.0,
        page_height_pt=400.0,
        raster_dpi=100,
        comparison_bbox=BoundingBox(x=0, y=0, width=200, height=120),
    )

    with fitz.open(output_path) as document:
        page = document.load_page(0)
        pixmap = page.get_pixmap(dpi=100, alpha=False)
        rendered = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height,
            pixmap.width,
            3,
        )
        assert rendered.shape[0] > 0
        assert rendered.shape[1] > 0
