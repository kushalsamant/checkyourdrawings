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


def resize_to_match(
    image: NDArray[np.generic],
    target_image: NDArray[np.generic],
    *,
    interpolation: int = cv2.INTER_AREA,
) -> ImageArray:
    """Resize an image to match the width and height of a target image."""
    _ensure_non_empty_image(image, name="image")
    _ensure_non_empty_image(target_image, name="target_image")

    if image.ndim not in (2, 3):
        raise ValueError("image must be a 2D grayscale or 3D color array.")

    if target_image.ndim not in (2, 3):
        raise ValueError("target_image must be a 2D grayscale or 3D color array.")

    target_height: int = int(target_image.shape[0])
    target_width: int = int(target_image.shape[1])

    resized: NDArray[np.generic] = cv2.resize(
        image,
        (target_width, target_height),
        interpolation=interpolation,
    )

    return normalize_image(resized)


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


def denoise_image(
    image: NDArray[np.generic],
    *,
    strength: float = 10.0,
    template_window_size: int = 7,
    search_window_size: int = 21,
) -> ImageArray:
    """Reduce image noise using OpenCV non-local means denoising."""
    normalized_image: ImageArray = normalize_image(image)

    if normalized_image.ndim == 2:
        return cv2.fastNlMeansDenoising(
            normalized_image,
            None,
            h=strength,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size,
        )

    if normalized_image.ndim == 3 and normalized_image.shape[2] in (3, 4):
        color_image: ImageArray = (
            cv2.cvtColor(normalized_image, cv2.COLOR_BGRA2BGR)
            if normalized_image.shape[2] == 4
            else normalized_image
        )

        return cv2.fastNlMeansDenoisingColored(
            color_image,
            None,
            h=strength,
            hColor=strength,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size,
        )

    raise ValueError("image must be a 2D grayscale or 3D color array.")


def threshold_image(
    image: NDArray[np.generic],
    *,
    threshold: int | None = None,
    max_value: int = 255,
    invert: bool = False,
) -> ImageArray:
    """Convert an image to a binary grayscale image."""
    grayscale: ImageArray = convert_to_grayscale(image)

    if not 0 <= max_value <= 255:
        raise ValueError("max_value must be between 0 and 255.")

    threshold_type: int = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY

    if threshold is None:
        _, binary = cv2.threshold(
            grayscale,
            0,
            max_value,
            threshold_type | cv2.THRESH_OTSU,
        )
        return binary

    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255.")

    _, binary = cv2.threshold(grayscale, threshold, max_value, threshold_type)
    return binary


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
