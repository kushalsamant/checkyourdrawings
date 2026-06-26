#!/usr/bin/env python3
"""Render level3 overlay PNGs at different agree-dilation radii for visual review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS, PDF_DPI
from backend.app.services.alignment import (
    align_drawing_b_to_a,
    max_features_for_image,
    refine_crop_alignment,
    use_ecc_refinement_for_images,
)
from backend.app.services.comparison_pipeline import _build_comparison_crops, _pillow_to_bgr_array
from backend.app.services.content_detection import detect_content_bbox, union_bbox
from backend.app.services.image_limits import choose_output_dpi
from backend.app.services.overlay_renderer import append_coordination_footer, render_coordination_overlay
from backend.app.services.pdf_converter import load_image, load_image_with_page_info
from backend.tests.fixtures.mvp_assets import _fixture_path

EXPECTED_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "expected"


def _render_level3_overlay(*, agree_dilation_radius: int) -> Path:
    drawing_a = _fixture_path("level3", "a")
    drawing_b = _fixture_path("level3", "b")

    drawing_a_pil, drawing_a_page = load_image_with_page_info(drawing_a)
    drawing_a_image = _pillow_to_bgr_array(drawing_a_pil)
    drawing_b_image = _pillow_to_bgr_array(load_image(drawing_b))

    aligned_drawing_b, alignment_metadata = align_drawing_b_to_a(
        drawing_a_image,
        drawing_b_image,
        max_features=max_features_for_image(drawing_a_image),
        ecc_refinement=use_ecc_refinement_for_images(drawing_a_image, drawing_b_image),
    )

    comparison_bbox = union_bbox(
        detect_content_bbox(drawing_a_image),
        detect_content_bbox(aligned_drawing_b),
    )
    output_dpi = choose_output_dpi(
        comparison_bbox.width,
        comparison_bbox.height,
        alignment_dpi=drawing_a_page.raster_dpi,
        preferred_dpi=PDF_DPI,
        max_pixels=MAX_IMAGE_PIXELS,
        max_dimension=MAX_IMAGE_DIMENSION,
    )
    drawing_a_crop, aligned_drawing_b_crop = _build_comparison_crops(
        drawing_a,
        drawing_b,
        drawing_a_image,
        drawing_b_image,
        aligned_drawing_b,
        comparison_bbox,
        alignment_metadata=alignment_metadata,
        alignment_dpi=drawing_a_page.raster_dpi,
        output_dpi=output_dpi,
    )
    aligned_drawing_b_crop = refine_crop_alignment(drawing_a_crop, aligned_drawing_b_crop)

    import backend.app.services.overlay_renderer as overlay_renderer

    original_radius = overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS
    try:
        overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS = agree_dilation_radius
        overlay_map, _stats = render_coordination_overlay(
            drawing_a_crop,
            aligned_drawing_b_crop,
            drawing_a_name=drawing_a.name,
            drawing_b_name=drawing_b.name,
            include_footer=False,
        )
    finally:
        overlay_renderer.OVERLAY_AGREE_DILATION_RADIUS = original_radius

    rendered = append_coordination_footer(
        overlay_map,
        drawing_a_name=drawing_a.name,
        drawing_b_name=drawing_b.name,
    )

    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EXPECTED_DIR / f"level3_overlay_dilation{agree_dilation_radius}.png"
    if not cv2.imwrite(str(output_path), rendered):
        raise ValueError(f"Failed to write overlay image: {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render level3 dilation A/B overlays.")
    parser.add_argument(
        "--radii",
        type=int,
        nargs="+",
        default=[2, 3],
        help="Agree-dilation radii to render (default: 2 3)",
    )
    args = parser.parse_args()

    for radius in args.radii:
        path = _render_level3_overlay(agree_dilation_radius=radius)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
