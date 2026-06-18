from __future__ import annotations

import io
from enum import Enum
from pathlib import Path
from typing import Literal

import fitz
import numpy as np
from PIL import Image, ImageDraw

FileExtension = Literal[".pdf", ".png", ".jpg", ".jpeg"]


class ContentScenario(str, Enum):
    IDENTICAL = "identical"
    B_ONLY_INK = "b_only_ink"
    A_ONLY_INK = "a_only_ink"
    MODIFIED_INK = "modified_ink"
    MIXED_INK = "mixed_ink"


def make_drawing_on_canvas(
    canvas_width: int,
    canvas_height: int,
    inset_x: int,
    inset_y: int,
    drawing_width: int = 320,
    drawing_height: int = 220,
) -> Image.Image:
    """Place the standard test drawing on a pure-white canvas with configurable margins."""
    canvas = Image.new("RGB", (canvas_width, canvas_height), color=(255, 255, 255))
    drawing = _make_core_drawing(drawing_width, drawing_height)
    canvas.paste(drawing, (inset_x, inset_y))
    return canvas


def make_padded_identical_pair(
    margin_a: tuple[int, int, int, int],
    margin_b: tuple[int, int, int, int],
    *,
    drawing_width: int = 320,
    drawing_height: int = 220,
) -> tuple[Image.Image, Image.Image]:
    """Return two canvases with identical ink but different white margins."""
    left_a, top_a, right_a, bottom_a = margin_a
    left_b, top_b, right_b, bottom_b = margin_b

    canvas_a = make_drawing_on_canvas(
        drawing_width + left_a + right_a,
        drawing_height + top_a + bottom_a,
        left_a,
        top_a,
        drawing_width=drawing_width,
        drawing_height=drawing_height,
    )
    canvas_b = make_drawing_on_canvas(
        drawing_width + left_b + right_b,
        drawing_height + top_b + bottom_b,
        left_b,
        top_b,
        drawing_width=drawing_width,
        drawing_height=drawing_height,
    )
    return canvas_a, canvas_b


def _make_core_drawing(width: int = 320, height: int = 220) -> Image.Image:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 120, 80), outline=(0, 0, 0), width=3)
    draw.rectangle((180, 20, 280, 80), fill=(0, 0, 0))
    draw.line((20, 140, 300, 140), fill=(0, 0, 0), width=2)
    draw.line((20, 20, 300, 180), fill=(128, 128, 128), width=1)
    draw.ellipse((220, 100, 300, 180), outline=(0, 0, 0), width=2)
    draw.text((30, 100), "Drawing A", fill=(0, 0, 0))
    return image


def make_drawing_a_image(width: int = 400, height: int = 300) -> Image.Image:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 180, 120), outline=(0, 0, 0), width=3)
    draw.rectangle((250, 40, 360, 120), fill=(0, 0, 0))
    draw.line((40, 200, 360, 200), fill=(0, 0, 0), width=2)
    draw.line((40, 40, 360, 260), fill=(128, 128, 128), width=1)
    draw.ellipse((300, 150, 380, 230), outline=(0, 0, 0), width=2)
    draw.text((50, 150), "Drawing A", fill=(0, 0, 0))

    for x in range(20, width, 40):
        draw.line((x, 0, x, height), fill=(220, 220, 220), width=1)

    return image


def make_drawing_b_image(scenario: ContentScenario, drawing_a: Image.Image | None = None) -> Image.Image:
    base = drawing_a.copy() if drawing_a is not None else make_drawing_a_image()
    draw = ImageDraw.Draw(base)

    if scenario == ContentScenario.IDENTICAL:
        return base

    if scenario == ContentScenario.B_ONLY_INK:
        draw.rectangle((200, 180, 280, 240), outline=(0, 0, 0), width=4)
        draw.line((200, 180, 280, 240), fill=(0, 0, 0), width=2)
        return base

    if scenario == ContentScenario.A_ONLY_INK:
        cleared = base.copy()
        cleared_draw = ImageDraw.Draw(cleared)
        cleared_draw.rectangle((250, 40, 360, 120), fill=(255, 255, 255))
        return cleared

    if scenario == ContentScenario.MODIFIED_INK:
        draw.rectangle((40, 40, 180, 120), outline=(0, 0, 0), width=5)
        draw.line((40, 200, 360, 220), fill=(0, 0, 0), width=2)
        return base

    if scenario == ContentScenario.MIXED_INK:
        draw.rectangle((250, 40, 360, 120), outline=(0, 0, 0), width=3)
        draw.rectangle((40, 40, 180, 120), fill=(255, 255, 255))
        draw.line((40, 200, 360, 240), fill=(0, 0, 0), width=3)
        return base

    raise ValueError(f"Unsupported scenario: {scenario}")


def image_to_bytes(image: Image.Image, extension: FileExtension) -> bytes:
    buffer = io.BytesIO()

    if extension == ".png":
        image.save(buffer, format="PNG")
    elif extension in {".jpg", ".jpeg"}:
        image.save(buffer, format="JPEG", quality=95)
    elif extension == ".pdf":
        return image_to_pdf_bytes(image)

    return buffer.getvalue()


def image_to_pdf_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    document = fitz.open()
    page = document.new_page(width=image.width, height=image.height)
    page.insert_image(page.rect, stream=image_to_png_bytes(image))
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_file_bytes(extension: FileExtension, scenario: ContentScenario) -> tuple[bytes, bytes]:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(scenario, drawing_a)
    return (
        image_to_bytes(drawing_a, extension),
        image_to_bytes(drawing_b, extension),
    )


def write_bytes(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def bgr_array_from_image(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return rgb[:, :, ::-1].copy()
