"""Optional debug artifact export for compare pipeline diagnosis."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.app.config import COMPARE_DEBUG, OUTPUT_DIR


def save_debug_frame(name: str, image: NDArray[np.generic], *, run_id: str | None = None) -> Path | None:
    """Write an intermediate frame when COMPARE_DEBUG is enabled."""
    if not COMPARE_DEBUG:
        return None

    debug_dir = OUTPUT_DIR / "debug"
    if run_id:
        debug_dir = debug_dir / run_id
    debug_dir.mkdir(parents=True, exist_ok=True)

    output_path = debug_dir / f"{name}.png"
    if not cv2.imwrite(str(output_path), image):
        raise ValueError(f"Failed to write debug frame: {output_path}")
    return output_path
