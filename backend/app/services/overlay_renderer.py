from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.config import MIN_INK_PIXEL_RATIO, OVERLAY_AGREE_DILATION_RADIUS
from backend.app.services.alignment import AlignmentError
from backend.app.services.image_utils import ImageArray, build_foreground_mask, convert_to_grayscale

CLASH_DILATION_RADIUS: Final[int] = 3

LIGHT_BACKGROUND: Final[tuple[int, int, int]] = (255, 255, 255)
ORANGE: Final[tuple[int, int, int]] = (0, 128, 255)
LIGHT_BLUE: Final[tuple[int, int, int]] = (220, 100, 40)
LIGHT_GREEN: Final[tuple[int, int, int]] = (40, 180, 40)
RED: Final[tuple[int, int, int]] = (0, 0, 255)
LIGHT_FOOTER_TEXT: Final[tuple[int, int, int]] = (20, 20, 20)

FOOTER_LEGEND: Final[str] = (
    "Orange = only in A | Blue = only in B | Green = in both | Red = clash"
)

INSUFFICIENT_INK_MESSAGE: Final[str] = (
    "Could not detect enough drawing content in the overlay. "
    "Try a vector PDF export or a higher-quality plot."
)


@dataclass(frozen=True)
class OverlayStats:
    orange_pixels: int
    blue_pixels: int
    green_pixels: int
    red_pixels: int


def validate_overlay_stats(
    stats: OverlayStats,
    *,
    crop_pixel_count: int,
    min_ink_pixel_ratio: float = MIN_INK_PIXEL_RATIO,
) -> None:
    """Reject compares that produced an effectively blank coordination map."""
    ink_pixels = (
        stats.orange_pixels
        + stats.blue_pixels
        + stats.green_pixels
        + stats.red_pixels
    )
    if crop_pixel_count <= 0:
        raise AlignmentError(INSUFFICIENT_INK_MESSAGE)

    if ink_pixels / crop_pixel_count < min_ink_pixel_ratio:
        raise AlignmentError(INSUFFICIENT_INK_MESSAGE)


@dataclass(frozen=True)
class OverlayPalette:
    background: tuple[int, int, int]
    orange: tuple[int, int, int]
    blue: tuple[int, int, int]
    green: tuple[int, int, int]
    red: tuple[int, int, int]
    footer_background: tuple[int, int, int]
    footer_text: tuple[int, int, int]


def render_coordination_overlay(
    drawing_a_image: NDArray[np.generic],
    aligned_drawing_b_image: NDArray[np.generic],
    *,
    drawing_a_name: str,
    drawing_b_name: str,
    low_confidence: bool = False,
    timestamp: datetime | None = None,
    include_footer: bool = True,
) -> tuple[ImageArray, OverlayStats]:
    """Render coordination overlay: orange/blue/green/red ink map."""
    if drawing_a_image.shape[:2] != aligned_drawing_b_image.shape[:2]:
        raise ValueError("drawing_a_image and aligned_drawing_b_image must share width and height.")

    palette = _light_palette()
    a_mask, b_mask = _build_ink_masks(drawing_a_image, aligned_drawing_b_image)
    classified = _classify_pixels(
        a_mask,
        b_mask,
        agree_dilation_radius=OVERLAY_AGREE_DILATION_RADIUS,
    )

    stats = OverlayStats(
        orange_pixels=int(classified["a_only"].sum()),
        blue_pixels=int(classified["b_only"].sum()),
        green_pixels=int(classified["agree"].sum()),
        red_pixels=int(classified["clash"].sum()),
    )

    output = _render_coordination_map(classified, palette, drawing_a_image.shape[:2])

    if not include_footer:
        return output, stats

    stamped = append_coordination_footer(
        output,
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        palette=palette,
        low_confidence=low_confidence,
        timestamp=timestamp or datetime.now(timezone.utc),
    )
    return stamped, stats


def append_coordination_footer(
    image: ImageArray,
    *,
    drawing_a_name: str,
    drawing_b_name: str,
    palette: OverlayPalette | None = None,
    low_confidence: bool = False,
    timestamp: datetime | None = None,
) -> ImageArray:
    """Append the metadata footer band below a coordination map image."""
    return _append_footer_band(
        image,
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        palette=palette or _light_palette(),
        low_confidence=low_confidence,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


def _render_coordination_map(
    classified: dict[str, NDArray[np.bool_]],
    palette: OverlayPalette,
    shape: tuple[int, int],
) -> ImageArray:
    output = np.full(shape + (3,), palette.background, dtype=np.uint8)
    output[classified["a_only"]] = palette.orange
    output[classified["b_only"]] = palette.blue
    output[classified["agree"]] = palette.green
    output[classified["clash"]] = palette.red
    return output


def _build_ink_masks(
    drawing_a_image: NDArray[np.generic],
    aligned_drawing_b_image: NDArray[np.generic],
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    drawing_a_gray = convert_to_grayscale(drawing_a_image)
    drawing_b_gray = convert_to_grayscale(aligned_drawing_b_image)
    a_mask = build_foreground_mask(drawing_a_gray) > 0
    b_mask = build_foreground_mask(drawing_b_gray) > 0
    return a_mask, b_mask


def _classify_pixels(
    a_mask: NDArray[np.bool_],
    b_mask: NDArray[np.bool_],
    *,
    agree_dilation_radius: int = OVERLAY_AGREE_DILATION_RADIUS,
) -> dict[str, NDArray[np.bool_]]:
    if agree_dilation_radius > 0:
        agree_kernel_size = agree_dilation_radius * 2 + 1
        agree_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (agree_kernel_size, agree_kernel_size),
        )
        a_for_agree = cv2.dilate(a_mask.astype(np.uint8), agree_kernel) > 0
        b_for_agree = cv2.dilate(b_mask.astype(np.uint8), agree_kernel) > 0
        agree = a_for_agree & b_for_agree
    else:
        agree = a_mask & b_mask

    a_only = a_mask & ~agree
    b_only = b_mask & ~agree

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


def _light_palette() -> OverlayPalette:
    return OverlayPalette(
        background=LIGHT_BACKGROUND,
        orange=ORANGE,
        blue=LIGHT_BLUE,
        green=LIGHT_GREEN,
        red=RED,
        footer_background=LIGHT_BACKGROUND,
        footer_text=LIGHT_FOOTER_TEXT,
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
        FOOTER_LEGEND,
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
