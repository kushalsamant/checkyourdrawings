from typing import Final

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.services.differencer import DifferenceKind, DifferenceResult
from backend.app.services.image_utils import ImageArray, normalize_image


Color = tuple[int, int, int]

ADDITION_COLOR: Final[Color] = (40, 180, 40)
DELETION_COLOR: Final[Color] = (40, 40, 220)
MODIFICATION_COLOR: Final[Color] = (0, 215, 255)
TEXT_COLOR: Final[Color] = (20, 20, 20)
TEXT_BACKGROUND_COLOR: Final[Color] = (255, 255, 255)
LEGEND_BACKGROUND_COLOR: Final[Color] = (245, 245, 245)
LEGEND_BORDER_COLOR: Final[Color] = (180, 180, 180)


def render_comparison_image(
    base_image: NDArray[np.generic],
    difference_result: DifferenceResult,
    *,
    title: str = "Drawing Comparison",
    box_thickness: int = 2,
) -> ImageArray:
    """Render differences over an image as a downloadable OpenCV BGR image."""
    if box_thickness < 1:
        raise ValueError("box_thickness must be greater than zero.")

    output_image: ImageArray = _to_bgr_image(base_image)

    for index, region in enumerate(difference_result.regions, start=1):
        color: Color = _color_for_kind(region.kind)
        box = region.bounding_box
        top_left: tuple[int, int] = (box.x, box.y)
        bottom_right: tuple[int, int] = (box.x + box.width, box.y + box.height)

        cv2.rectangle(
            output_image,
            top_left,
            bottom_right,
            color,
            thickness=box_thickness,
            lineType=cv2.LINE_AA,
        )

        label: str = f"{index}. {region.kind} ({region.confidence:.0%})"
        _draw_label(output_image, label=label, anchor=top_left, color=color)

    _draw_legend(output_image, title=title, difference_result=difference_result)
    return output_image


def encode_comparison_png(image: NDArray[np.generic]) -> bytes:
    """Encode a rendered comparison image as PNG bytes for HTTP download responses."""
    bgr_image: ImageArray = _to_bgr_image(image)
    success: bool
    encoded: NDArray[np.uint8]
    success, encoded = cv2.imencode(".png", bgr_image)

    if not success:
        raise ValueError("Could not encode comparison image as PNG.")

    return encoded.tobytes()


def _to_bgr_image(image: NDArray[np.generic]) -> ImageArray:
    if image.size == 0:
        raise ValueError("image must not be empty.")

    normalized: ImageArray = normalize_image(image)

    if normalized.ndim == 2:
        return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)

    if normalized.ndim == 3 and normalized.shape[2] == 3:
        return normalized.copy()

    if normalized.ndim == 3 and normalized.shape[2] == 4:
        return cv2.cvtColor(normalized, cv2.COLOR_BGRA2BGR)

    raise ValueError("image must be a 2D grayscale, 3-channel BGR, or 4-channel BGRA array.")


def _draw_label(
    image: ImageArray,
    *,
    label: str,
    anchor: tuple[int, int],
    color: Color,
) -> None:
    font_face: int = cv2.FONT_HERSHEY_SIMPLEX
    font_scale: float = 0.5
    thickness: int = 1
    padding: int = 4

    text_width: int
    text_height: int
    baseline: int
    (text_width, text_height), baseline = cv2.getTextSize(
        label,
        font_face,
        font_scale,
        thickness,
    )

    x: int = max(0, anchor[0])
    y: int = max(text_height + padding * 2, anchor[1])

    background_top_left: tuple[int, int] = (x, y - text_height - padding * 2)
    background_bottom_right: tuple[int, int] = (
        min(image.shape[1] - 1, x + text_width + padding * 2),
        min(image.shape[0] - 1, y + baseline),
    )

    cv2.rectangle(
        image,
        background_top_left,
        background_bottom_right,
        TEXT_BACKGROUND_COLOR,
        thickness=-1,
    )
    cv2.rectangle(
        image,
        background_top_left,
        background_bottom_right,
        color,
        thickness=1,
    )
    cv2.putText(
        image,
        label,
        (x + padding, y - padding),
        font_face,
        font_scale,
        TEXT_COLOR,
        thickness,
        lineType=cv2.LINE_AA,
    )


def _draw_legend(
    image: ImageArray,
    *,
    title: str,
    difference_result: DifferenceResult,
) -> None:
    font_face: int = cv2.FONT_HERSHEY_SIMPLEX
    title_scale: float = 0.6
    item_scale: float = 0.5
    thickness: int = 1
    padding: int = 10
    swatch_size: int = 14
    line_gap: int = 24

    items: list[tuple[str, Color]] = [
        ("Additions", ADDITION_COLOR),
        ("Deletions", DELETION_COLOR),
        ("Modifications", MODIFICATION_COLOR),
    ]

    summary: str = (
        f"Regions: {len(difference_result.regions)} | "
        f"Changed: {difference_result.changed_pixel_ratio:.2%}"
    )
    text_lines: list[str] = [title, summary, *[item[0] for item in items]]

    legend_width: int = max(
        cv2.getTextSize(line, font_face, title_scale if index == 0 else item_scale, thickness)[0][0]
        for index, line in enumerate(text_lines)
    )
    legend_width += padding * 3 + swatch_size
    legend_height: int = padding * 2 + 22 + line_gap * (len(items) + 1)

    x1: int = padding
    y1: int = padding
    x2: int = min(image.shape[1] - 1, x1 + legend_width)
    y2: int = min(image.shape[0] - 1, y1 + legend_height)

    overlay: ImageArray = image.copy()
    cv2.rectangle(
        overlay,
        (x1, y1),
        (x2, y2),
        LEGEND_BACKGROUND_COLOR,
        thickness=-1,
    )
    cv2.addWeighted(overlay, 0.88, image, 0.12, 0, dst=image)
    cv2.rectangle(image, (x1, y1), (x2, y2), LEGEND_BORDER_COLOR, thickness=1)

    current_y: int = y1 + padding + 12
    cv2.putText(
        image,
        title,
        (x1 + padding, current_y),
        font_face,
        title_scale,
        TEXT_COLOR,
        thickness,
        lineType=cv2.LINE_AA,
    )

    current_y += line_gap
    cv2.putText(
        image,
        summary,
        (x1 + padding, current_y),
        font_face,
        item_scale,
        TEXT_COLOR,
        thickness,
        lineType=cv2.LINE_AA,
    )

    for label, color in items:
        current_y += line_gap
        swatch_top_left: tuple[int, int] = (x1 + padding, current_y - swatch_size + 3)
        swatch_bottom_right: tuple[int, int] = (
            x1 + padding + swatch_size,
            current_y + 3,
        )
        cv2.rectangle(image, swatch_top_left, swatch_bottom_right, color, thickness=-1)
        cv2.rectangle(
            image,
            swatch_top_left,
            swatch_bottom_right,
            LEGEND_BORDER_COLOR,
            thickness=1,
        )
        cv2.putText(
            image,
            label,
            (x1 + padding * 2 + swatch_size, current_y),
            font_face,
            item_scale,
            TEXT_COLOR,
            thickness,
            lineType=cv2.LINE_AA,
        )


def _color_for_kind(kind: DifferenceKind) -> Color:
    if kind == "addition":
        return ADDITION_COLOR

    if kind == "deletion":
        return DELETION_COLOR

    return MODIFICATION_COLOR
