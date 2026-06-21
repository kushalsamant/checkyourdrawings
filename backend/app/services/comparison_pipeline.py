import gc
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image

from backend.app.config import OUTPUT_DIR, OUTPUT_MAX_AGE_HOURS
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import (
    AlignmentError,
    align_drawing_b_to_a,
    evaluate_alignment_confidence,
    max_features_for_image,
    use_ecc_refinement_for_images,
)
from backend.app.services.content_detection import (
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
    union_bbox,
)
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.overlay_renderer import render_coordination_overlay
from backend.app.services.pdf_converter import load_image, load_image_with_page_info
from backend.app.services.pdf_exporter import save_overlay_pdf


def run_comparison_pipeline(
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
) -> CompareResponse:
    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)

    drawing_a_image_pil, drawing_a_page = load_image_with_page_info(drawing_a_path)
    drawing_a_image = _pillow_to_bgr_array(drawing_a_image_pil)
    drawing_b_image = _pillow_to_bgr_array(load_image(drawing_b_path))

    try:
        aligned_drawing_b, alignment_metadata = align_drawing_b_to_a(
            drawing_a_image,
            drawing_b_image,
            max_features=max_features_for_image(drawing_a_image),
            ecc_refinement=use_ecc_refinement_for_images(
                drawing_a_image,
                drawing_b_image,
            ),
        )
        alignment_confidence = evaluate_alignment_confidence(alignment_metadata)

        drawing_a_bbox = detect_content_bbox(drawing_a_image)
        drawing_b_bbox = detect_content_bbox(aligned_drawing_b)
        overlap_bbox = compute_overlap_bbox(drawing_a_bbox, drawing_b_bbox)
        if overlap_bbox is None:
            raise AlignmentError(
                "Could not find enough overlapping drawing content between the two files. "
                "They may show different views or have incompatible framing."
            )

        comparison_bbox = union_bbox(drawing_a_bbox, drawing_b_bbox)
        drawing_a_crop = crop_image(drawing_a_image, comparison_bbox)
        aligned_drawing_b_crop = crop_image(aligned_drawing_b, comparison_bbox)

        rendered_image, overlay_stats = render_coordination_overlay(
            drawing_a_crop,
            aligned_drawing_b_crop,
            drawing_a_name=drawing_a_name,
            drawing_b_name=drawing_b_name,
            low_confidence=alignment_confidence.status == "marginal",
        )

        output_id = uuid4().hex
        output_filename = f"comparison-{output_id}.png"
        pdf_filename = f"comparison-{output_id}.pdf"
        output_path = OUTPUT_DIR / output_filename
        pdf_path = OUTPUT_DIR / pdf_filename

        if not cv2.imwrite(str(output_path), rendered_image):
            raise ValueError("Failed to save comparison image.")

        save_overlay_pdf(
            pdf_path,
            rendered_image,
            page_width_pt=drawing_a_page.page_width_pt,
            page_height_pt=drawing_a_page.page_height_pt,
            raster_dpi=drawing_a_page.raster_dpi,
            comparison_bbox=comparison_bbox,
        )

        changed_pixels = (
            overlay_stats.orange_pixels
            + overlay_stats.blue_pixels
            + overlay_stats.red_pixels
        )
        total_pixels = max(
            1,
            overlay_stats.orange_pixels
            + overlay_stats.blue_pixels
            + overlay_stats.green_pixels
            + overlay_stats.red_pixels,
        )

        return CompareResponse.from_pipeline_result(
            image_path=f"/outputs/{output_filename}",
            pdf_path=f"/outputs/{pdf_filename}",
            metadata={
                "alignment": asdict(alignment_metadata),
                "alignment_confidence": asdict(alignment_confidence),
                "content": {
                    "drawing_a_bbox": asdict(drawing_a_bbox),
                    "drawing_b_bbox": asdict(drawing_b_bbox),
                    "overlap_bbox": asdict(overlap_bbox),
                    "comparison_bbox": asdict(comparison_bbox),
                },
                "overlay": asdict(overlay_stats),
                "differences": {
                    "width": int(comparison_bbox.width),
                    "height": int(comparison_bbox.height),
                    "changed_pixel_count": changed_pixels,
                    "changed_pixel_ratio": changed_pixels / total_pixels,
                },
                "output_page": {
                    "mode": "source_a",
                    "width_pt": drawing_a_page.page_width_pt,
                    "height_pt": drawing_a_page.page_height_pt,
                    "raster_dpi": drawing_a_page.raster_dpi,
                },
            },
        )
    finally:
        del drawing_a_image
        del drawing_b_image
        if "aligned_drawing_b" in locals():
            del aligned_drawing_b
        gc.collect()


def _pillow_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb_image: Image.Image = image.convert("RGB")
    rgb_array = np.asarray(rgb_image, dtype=np.uint8)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
