from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.services.image_utils import ImageArray, build_foreground_mask, convert_to_grayscale


BackgroundMode = Literal["light", "dark"]

CLASH_DILATION_RADIUS: Final[int] = 3


@dataclass(frozen=True)
class OverlayStats:
    red_pixels: int
    blue_pixels: int
    green_pixels: int
    magenta_pixels: int
    background_mode: BackgroundMode


@dataclass(frozen=True)
class OverlayPalette:
    background: tuple[int, int, int]
    red: tuple[int, int, int]
    blue: tuple[int, int, int]
    green: tuple[int, int, int]
    magenta: tuple[int, int, int]
    footer_background: tuple[int, int, int]
    footer_text: tuple[int, int, int]


def render_coordination_overlay(
    reference_image: NDArray[np.generic],
    aligned_image: NDArray[np.generic],
    *,
    drawing_a_name: str,
    drawing_b_name: str,
    background_mode: BackgroundMode = "light",
    low_confidence: bool = False,
    timestamp: datetime | None = None,
) -> tuple[ImageArray, OverlayStats]:
    """Align-then-classify: per-pixel ink overlay with footer band."""
    if reference_image.shape[:2] != aligned_image.shape[:2]:
        raise ValueError("reference_image and aligned_image must share width and height.")

    palette = _palette_for_mode(background_mode)
    a_mask, b_mask = _build_ink_masks(reference_image, aligned_image)
    classified = _classify_pixels(a_mask, b_mask)

    output = np.full(reference_image.shape[:2] + (3,), palette.background, dtype=np.uint8)
    output[classified["a_only"]] = palette.red
    output[classified["b_only"]] = palette.blue
    output[classified["agree"]] = palette.green
    output[classified["clash"]] = palette.magenta

    stats = OverlayStats(
        red_pixels=int(classified["a_only"].sum()),
        blue_pixels=int(classified["b_only"].sum()),
        green_pixels=int(classified["agree"].sum()),
        magenta_pixels=int(classified["clash"].sum()),
        background_mode=background_mode,
    )

    stamped = _append_footer_band(
        output,
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        palette=palette,
        low_confidence=low_confidence,
        timestamp=timestamp or datetime.now(timezone.utc),
    )
    return stamped, stats


def _build_ink_masks(
    reference_image: NDArray[np.generic],
    aligned_image: NDArray[np.generic],
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    reference_gray = convert_to_grayscale(reference_image)
    aligned_gray = convert_to_grayscale(aligned_image)
    a_mask = build_foreground_mask(reference_gray) > 0
    b_mask = build_foreground_mask(aligned_gray) > 0
    return a_mask, b_mask


def _classify_pixels(
    a_mask: NDArray[np.bool_],
    b_mask: NDArray[np.bool_],
) -> dict[str, NDArray[np.bool_]]:
    agree = a_mask & b_mask
    a_only = a_mask & ~b_mask
    b_only = b_mask & ~a_mask

    kernel_size = CLASH_DILATION_RADIUS * 2 + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    a_dilated = cv2.dilate(a_mask.astype(np.uint8), kernel) > 0
    b_dilated = cv2.dilate(b_mask.astype(np.uint8), kernel) > 0
    clash = (a_mask & b_dilated) | (b_mask & a_dilated)
    clash &= ~agree
    a_only &= ~clash
    b_only &= ~clash

    return {
        "agree": agree,
        "a_only": a_only,
        "b_only": b_only,
        "clash": clash,
    }


def _palette_for_mode(mode: BackgroundMode) -> OverlayPalette:
    if mode == "dark":
        return OverlayPalette(
            background=(26, 26, 26),
            red=(80, 80, 255),
            blue=(255, 160, 80),
            green=(80, 255, 120),
            magenta=(255, 80, 255),
            footer_background=(26, 26, 26),
            footer_text=(255, 255, 255),
        )

    return OverlayPalette(
        background=(255, 255, 255),
        red=(40, 40, 220),
        blue=(220, 100, 40),
        green=(40, 180, 40),
        magenta=(220, 40, 220),
        footer_background=(255, 255, 255),
        footer_text=(20, 20, 20),
    )


def _append_footer_band(
    image: ImageArray,
    *,
    drawing_a_name: str,
    drawing_b_name: str,
    palette: OverlayPalette,
    low_confidence: bool,
    timestamp: datetime,
) -> ImageArray:
    footer_lines = [
        f"Drawing A: {drawing_a_name}",
        f"Drawing B: {drawing_b_name}",
        f"Timestamp: {timestamp.isoformat(timespec='seconds')}",
        "Red = only in A | Blue = only in B | Green = in both | Magenta = clash",
    ]
    if low_confidence:
        footer_lines.append("Low-confidence alignment")

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness = 1
    line_height = 22
    padding = 12
    max_text_width = max(image.shape[1] - padding * 2, 200)

    wrapped_lines: list[str] = []
    for line in footer_lines:
        wrapped_lines.extend(_wrap_footer_line(line, font, font_scale, thickness, max_text_width))

    footer_height = padding * 2 + line_height * len(wrapped_lines)
    footer = np.full((footer_height, image.shape[1], 3), palette.footer_background, dtype=np.uint8)

    y = padding + line_height - 6
    for line in wrapped_lines:
        cv2.putText(
            footer,
            line,
            (padding, y),
            font,
            font_scale,
            palette.footer_text,
            thickness,
            lineType=cv2.LINE_AA,
        )
        y += line_height

    return np.vstack([image, footer])


def _wrap_footer_line(
    line: str,
    font: int,
    font_scale: float,
    thickness: int,
    max_width: int,
) -> list[str]:
    if not line:
        return [""]

    words = line.split(" ")
    wrapped: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        size = cv2.getTextSize(candidate, font, font_scale, thickness)[0]
        if size[0] <= max_width:
            current = candidate
        else:
            wrapped.append(current)
            current = word

    wrapped.append(current)
    return wrapped
