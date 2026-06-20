from typing import Final

import cv2
import numpy as np

from backend.app.services.image_utils import ImageArray

WATERMARK_TEXT: Final[str] = "checkyourdrawings.kvshvl.in"


def apply_watermark(image: ImageArray, text: str = WATERMARK_TEXT) -> ImageArray:
    """Stamp a light diagonal watermark across the comparison image."""
    stamped = image.copy()
    height, width = stamped.shape[:2]
    overlay = np.zeros_like(stamped)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(width, height) / 2200.0
    thickness = max(2, int(round(font_scale * 2)))
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)

    step_x = text_width + max(80, width // 8)
    step_y = text_height + max(60, height // 10)
    color = (190, 190, 190)

    for y in range(-height, height * 2, step_y):
        offset_x = (y // step_y) % 2 * (step_x // 2)
        for x in range(-width, width * 2, step_x):
            cv2.putText(
                overlay,
                text,
                (x + offset_x, y),
                font,
                font_scale,
                color,
                thickness,
                lineType=cv2.LINE_AA,
            )

    return cv2.addWeighted(overlay, 0.28, stamped, 0.72, 0)
