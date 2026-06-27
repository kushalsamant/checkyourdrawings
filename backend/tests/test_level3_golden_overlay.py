"""Level3 golden overlay regression — palette-mask comparison wired to CI."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.tests.fixtures.mvp_assets import _fixture_path, require_mvp_assets
from backend.tests.fixtures.overlay_golden import (
    LEVEL3_GOLDEN_OVERLAY,
    classify_coordination_overlay,
    overlay_stats_from_labels,
    read_overlay_image,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Anti-aliased background pixels may differ slightly between runs; ink must match.
_MAX_NON_INK_LABEL_MISMATCH = 500


def test_level3_overlay_matches_golden_palette() -> None:
    """Compare level3 coordination map to committed golden via palette labels."""
    require_mvp_assets()
    if not LEVEL3_GOLDEN_OVERLAY.is_file():
        raise AssertionError(
            f"Golden overlay missing: {LEVEL3_GOLDEN_OVERLAY}. "
            "Run: python scripts/render_level3_golden.py"
        )

    drawing_a = _fixture_path("level3", "a")
    drawing_b = _fixture_path("level3", "b")
    result = run_comparison_pipeline(
        drawing_a,
        drawing_b,
        drawing_a.name,
        drawing_b.name,
    )

    generated_path = REPO_ROOT / "backend" / result.image_path.removeprefix("/")
    generated = read_overlay_image(generated_path)
    golden = read_overlay_image(LEVEL3_GOLDEN_OVERLAY)

    assert generated.shape == golden.shape, (
        f"Shape mismatch: generated {generated.shape} vs golden {golden.shape}"
    )

    generated_labels = classify_coordination_overlay(generated)
    golden_labels = classify_coordination_overlay(golden)

    golden_stats = overlay_stats_from_labels(golden_labels)
    overlay = result.metadata.overlay
    assert overlay.orange_pixels == golden_stats.orange_pixels
    assert overlay.blue_pixels == golden_stats.blue_pixels
    assert overlay.green_pixels == golden_stats.green_pixels
    assert overlay.red_pixels == golden_stats.red_pixels

    ink_mask = (golden_labels >= 1) & (golden_labels <= 4)
    ink_mismatch = int(np.count_nonzero((generated_labels != golden_labels) & ink_mask))
    assert ink_mismatch == 0, f"Ink palette labels differ on {ink_mismatch} pixels"

    non_ink_mismatch = int(np.count_nonzero((generated_labels != golden_labels) & ~ink_mask))
    assert non_ink_mismatch <= _MAX_NON_INK_LABEL_MISMATCH, (
        f"Background label drift too high: {non_ink_mismatch} pixels"
    )
