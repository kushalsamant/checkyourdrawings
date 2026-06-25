"""PDF fixtures that mimic architectural drawing exports."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from backend.tests.fixtures.factory import (
    ContentScenario,
    image_to_pdf_bytes,
    make_drawing_a_image,
    make_drawing_b_image,
    make_drawing_on_canvas,
    write_bytes,
)


class PdfFixturePair(str, Enum):
    IDENTICAL = "identical"
    LIGHT_LINEWORK = "light_linework"
    MARGIN_SHIFT = "margin_shift"
    MODIFIED = "modified"


def write_pdf_fixture_pair(
    directory: Path,
    pair: PdfFixturePair,
    *,
    page_width_pt: float = 842.0,
    page_height_pt: float = 595.0,
) -> tuple[Path, Path]:
    """Write Drawing A and Drawing B PDFs for an end-to-end pipeline scenario."""
    directory.mkdir(parents=True, exist_ok=True)
    drawing_a_path = directory / f"drawing_a_{pair.value}.pdf"
    drawing_b_path = directory / f"drawing_b_{pair.value}.pdf"

    if pair == PdfFixturePair.IDENTICAL:
        image = make_drawing_a_image(width=1200, height=900)
        write_bytes(drawing_a_path, image_to_pdf_bytes(image))
        write_bytes(drawing_b_path, image_to_pdf_bytes(image.copy()))
        return drawing_a_path, drawing_b_path

    if pair == PdfFixturePair.LIGHT_LINEWORK:
        drawing_a = _make_light_linework_sheet()
        drawing_b = drawing_a.copy()
        write_bytes(drawing_a_path, image_to_pdf_bytes(drawing_a))
        write_bytes(drawing_b_path, image_to_pdf_bytes(drawing_b))
        return drawing_a_path, drawing_b_path

    if pair == PdfFixturePair.MARGIN_SHIFT:
        drawing_a, drawing_b = _make_margin_shift_pair()
        write_bytes(drawing_a_path, image_to_pdf_bytes(drawing_a))
        write_bytes(drawing_b_path, image_to_pdf_bytes(drawing_b))
        return drawing_a_path, drawing_b_path

    if pair == PdfFixturePair.MODIFIED:
        drawing_a = make_drawing_a_image(width=1200, height=900)
        drawing_b = make_drawing_b_image(ContentScenario.MODIFIED_INK, drawing_a)
        write_bytes(drawing_a_path, image_to_pdf_bytes(drawing_a))
        write_bytes(drawing_b_path, image_to_pdf_bytes(drawing_b))
        return drawing_a_path, drawing_b_path

    raise ValueError(f"Unsupported fixture pair: {pair}")


def _make_light_linework_sheet() -> Image.Image:
    width_px = 800
    height_px = 600
    image = Image.new("RGB", (width_px, height_px), color=(235, 235, 235))
    draw = ImageDraw.Draw(image)

    for x in range(80, width_px - 80, 120):
        draw.line((x, 80, x, height_px - 80), fill=(170, 170, 170), width=1)

    for y in range(80, height_px - 80, 120):
        draw.line((80, y, width_px - 80, y), fill=(170, 170, 170), width=1)

    draw.rectangle((120, 100, 420, 320), outline=(120, 120, 120), width=2)
    draw.rectangle((480, 140, 640, 280), outline=(100, 100, 100), width=1)
    draw.line((120, 380, 640, 380), fill=(110, 110, 110), width=1)
    draw.text((140, 340), "LEVEL 01", fill=(90, 90, 90))
    return image


def _make_margin_shift_pair() -> tuple[Image.Image, Image.Image]:
    return (
        make_drawing_on_canvas(600, 450, 40, 30),
        make_drawing_on_canvas(600, 450, 80, 60),
    )


def write_pdf_page(
    path: Path,
    image: Image.Image,
    *,
    page_width_pt: float = 842.0,
    page_height_pt: float = 595.0,
) -> Path:
    """Write a single-page PDF with the image scaled to the page."""
    document = fitz.open()
    page = document.new_page(width=page_width_pt, height=page_height_pt)
    page.insert_image(page.rect, stream=_image_png_bytes(image))
    document.save(str(path))
    document.close()
    return path


def _image_png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
