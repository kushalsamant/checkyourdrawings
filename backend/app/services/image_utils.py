from typing import TypeAlias

import cv2
import numpy as np
from numpy.typing import NDArray


ImageArray: TypeAlias = NDArray[np.uint8]


def _ensure_non_empty_image(image: NDArray[np.generic], *, name: str) -> None:
    if image.size == 0:
        raise ValueError(f"{name} must not be empty.")


def convert_to_grayscale(image: NDArray[np.generic]) -> ImageArray:
    """Convert a BGR, BGRA, RGB-like, or grayscale image to grayscale."""
    _ensure_non_empty_image(image, name="image")

    if image.ndim == 2:
        return normalize_image(image)

    if image.ndim != 3:
        raise ValueError("image must be a 2D grayscale or 3D color array.")

    channels: int = image.shape[2]

    if channels == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if channels == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    raise ValueError("image must have 1, 3, or 4 channels.")


def normalize_image(image: NDArray[np.generic]) -> ImageArray:
    """Normalize an image to the 0-255 range as uint8."""
    _ensure_non_empty_image(image, name="image")

    if image.dtype == np.uint8:
        return image.copy()

    normalized: NDArray[np.generic] = cv2.normalize(
        image,
        None,
        alpha=0,
        beta=255,
        norm_type=cv2.NORM_MINMAX,
    )

    return normalized.astype(np.uint8, copy=False)


def clean_mask(mask: ImageArray, *, morphology_kernel_size: int) -> ImageArray:
    """Apply opening and closing to reduce noise in a binary mask."""
    if morphology_kernel_size < 1 or morphology_kernel_size % 2 == 0:
        raise ValueError("morphology_kernel_size must be a positive odd integer.")

    kernel: ImageArray = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (morphology_kernel_size, morphology_kernel_size),
    )

    opened: ImageArray = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)


def build_framing_mask(grayscale_image: ImageArray) -> ImageArray:
    """Build an ink mask for content framing without removing thin separated lines."""
    _, mask = cv2.threshold(
        grayscale_image,
        0,
        255,
        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
    )
    kernel: ImageArray = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)


def build_foreground_mask(
    grayscale_image: ImageArray,
    *,
    threshold: int | None = None,
    morphology_kernel_size: int = 3,
) -> ImageArray:
    """Build a binary mask of ink-like foreground pixels."""
    if threshold is None:
        _, mask = cv2.threshold(
            grayscale_image,
            0,
            255,
            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
        )
    else:
        if not 0 <= threshold <= 255:
            raise ValueError("threshold must be between 0 and 255.")

        _, mask = cv2.threshold(
            grayscale_image,
            threshold,
            255,
            cv2.THRESH_BINARY_INV,
        )

    return clean_mask(mask, morphology_kernel_size=morphology_kernel_size)
