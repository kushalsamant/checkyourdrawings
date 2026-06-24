from __future__ import annotations

from pathlib import Path

import cv2
import fitz
import numpy as np
from numpy.typing import NDArray

from backend.app.services.content_detection import BoundingBox


def save_overlay_pdf(
    output_path: Path,
    overlay_bgr: NDArray[np.generic],
    *,
    page_width_pt: float,
    page_height_pt: float,
    raster_dpi: int,
    comparison_bbox: BoundingBox,
    alignment_dpi: int | None = None,
) -> None:
    """Embed a lossless overlay PNG on a one-page PDF sized like Drawing A."""
    if raster_dpi <= 0:
        raise ValueError("raster_dpi must be greater than zero.")
    if page_width_pt <= 0 or page_height_pt <= 0:
        raise ValueError("page dimensions must be greater than zero.")

    encoded, png_bytes = cv2.imencode(".png", overlay_bgr)
    if not encoded:
        raise ValueError("Failed to encode overlay PNG.")

    overlay_height, overlay_width = overlay_bgr.shape[:2]
    bbox_dpi = alignment_dpi if alignment_dpi is not None else raster_dpi
    if bbox_dpi <= 0:
        raise ValueError("alignment_dpi must be greater than zero when provided.")

    x_pt = comparison_bbox.x / bbox_dpi * 72.0
    y_pt = comparison_bbox.y / bbox_dpi * 72.0
    width_pt = overlay_width / raster_dpi * 72.0
    height_pt = overlay_height / raster_dpi * 72.0
    image_rect = fitz.Rect(x_pt, y_pt, x_pt + width_pt, y_pt + height_pt)

    document = fitz.open()
    try:
        page = document.new_page(width=page_width_pt, height=page_height_pt)
        page.insert_image(image_rect, stream=png_bytes.tobytes())
        document.save(str(output_path))
    finally:
        document.close()
