#!/usr/bin/env python3
"""Write the canonical level3 golden overlay PNG for human sign-off."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.tests.fixtures.mvp_assets import _fixture_path

EXPECTED_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "expected"
ASSETS_GOLDEN = REPO_ROOT / "assets" / "sample-output-level3-from-assets.png"


def main() -> int:
    drawing_a = _fixture_path("level3", "a")
    drawing_b = _fixture_path("level3", "b")
    result = run_comparison_pipeline(drawing_a, drawing_b, drawing_a.name, drawing_b.name)

    source = REPO_ROOT / "backend" / result.image_path.removeprefix("/")
    if not source.is_file():
        raise FileNotFoundError(f"Comparison output not found: {source}")

    image = cv2.imread(str(source))
    if image is None:
        raise ValueError(f"Failed to read comparison output: {source}")

    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = EXPECTED_DIR / "level3_overlay.png"
    if not cv2.imwrite(str(golden_path), image):
        raise ValueError(f"Failed to write golden overlay: {golden_path}")

    ASSETS_GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(golden_path, ASSETS_GOLDEN)
    print(golden_path)
    print(ASSETS_GOLDEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
