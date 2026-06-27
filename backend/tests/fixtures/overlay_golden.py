"""Golden overlay helpers for level3 visual regression."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.services.overlay_renderer import (
    LIGHT_BACKGROUND,
    LIGHT_BLUE,
    LIGHT_GREEN,
    ORANGE,
    RED,
    OverlayStats,
)

EXPECTED_DIR = Path(__file__).resolve().parent / "expected"
LEVEL3_GOLDEN_OVERLAY = EXPECTED_DIR / "level3_overlay.png"

# BGR palette order used by classify_coordination_overlay().
_PALETTE_BGR: tuple[tuple[int, int, int], ...] = (
    LIGHT_BACKGROUND,
    ORANGE,
    LIGHT_BLUE,
    LIGHT_GREEN,
    RED,
)
_UNKNOWN_LABEL = 255


def classify_coordination_overlay(image: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Map each pixel to a stable palette label (255 = non-exact / anti-aliased)."""
    labels = np.full(image.shape[:2], _UNKNOWN_LABEL, dtype=np.uint8)
    for label, color in enumerate(_PALETTE_BGR):
        match = np.all(image == np.array(color, dtype=np.uint8), axis=2)
        labels[match] = label
    return labels


def overlay_stats_from_labels(labels: NDArray[np.uint8]) -> OverlayStats:
    """Count ink pixels from classified overlay labels (excludes background)."""
    return OverlayStats(
        orange_pixels=int(np.count_nonzero(labels == 1)),
        blue_pixels=int(np.count_nonzero(labels == 2)),
        green_pixels=int(np.count_nonzero(labels == 3)),
        red_pixels=int(np.count_nonzero(labels == 4)),
    )


def read_overlay_image(path: Path) -> NDArray[np.uint8]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Overlay image not found or unreadable: {path}")
    return image
