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
    ADDITION_ONLY = "addition_only"
    DELETION_ONLY = "deletion_only"
    MODIFICATION_ONLY = "modification_only"
    MIXED_ALL_THREE = "mixed_all_three"


def make_reference_image(width: int = 400, height: int = 300) -> Image.Image:
    image = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 180, 120), outline=(0, 0, 0), width=3)
    draw.rectangle((250, 40, 360, 120), fill=(0, 0, 0))
    draw.line((40, 200, 360, 200), fill=(0, 0, 0), width=2)
    draw.line((40, 40, 360, 260), fill=(128, 128, 128), width=1)
    draw.ellipse((300, 150, 380, 230), outline=(0, 0, 0), width=2)
    draw.text((50, 150), "Revision A", fill=(0, 0, 0))

    for x in range(20, width, 40):
        draw.line((x, 0, x, height), fill=(220, 220, 220), width=1)

    return image


def make_revision_image(scenario: ContentScenario, reference: Image.Image | None = None) -> Image.Image:
    base = reference.copy() if reference is not None else make_reference_image()
    draw = ImageDraw.Draw(base)

    if scenario == ContentScenario.IDENTICAL:
        return base

    if scenario == ContentScenario.ADDITION_ONLY:
        draw.rectangle((200, 180, 280, 240), outline=(0, 0, 0), width=4)
        draw.line((200, 180, 280, 240), fill=(0, 0, 0), width=2)
        return base

    if scenario == ContentScenario.DELETION_ONLY:
        cleared = base.copy()
        cleared_draw = ImageDraw.Draw(cleared)
        cleared_draw.rectangle((250, 40, 360, 120), fill=(255, 255, 255))
        return cleared

    if scenario == ContentScenario.MODIFICATION_ONLY:
        draw.rectangle((40, 40, 180, 120), outline=(0, 0, 0), width=5)
        draw.line((40, 200, 360, 220), fill=(0, 0, 0), width=2)
        return base

    if scenario == ContentScenario.MIXED_ALL_THREE:
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
    reference = make_reference_image()
    revision = make_revision_image(scenario, reference)
    return (
        image_to_bytes(reference, extension),
        image_to_bytes(revision, extension),
    )


def write_bytes(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def bgr_array_from_image(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return rgb[:, :, ::-1].copy()
