import gc
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from PIL import Image

from backend.app.config import (
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    PDF_DPI,
)
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import (
    AlignmentError,
    AlignmentMetadata,
    align_drawing_b_to_a,
    evaluate_alignment_confidence,
    max_features_for_image,
    refine_crop_alignment,
    scale_homography,
    use_ecc_refinement_for_images,
    warp_drawing_with_homography,
)
from backend.app.services.compare_debug import save_debug_frame
from backend.app.services.compare_stages import (
    STAGE_ALIGNING_SHEETS,
    STAGE_BUILDING_OVERLAY,
    STAGE_LOADING_DRAWINGS,
    STAGE_PREPARING_COMPARISON,
    STAGE_SAVING_RESULTS,
)
from backend.app.services.content_detection import (
    BoundingBox,
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
    scale_bbox,
    union_bbox,
)
from backend.app.services.image_limits import choose_output_dpi
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.overlay_renderer import (
    append_coordination_footer,
    render_coordination_overlay,
    validate_overlay_stats,
)
from backend.app.services.pdf_converter import (
    load_image,
    load_image_with_page_info,
    rasterize_pdf_bbox,
)
from backend.app.services.pdf_exporter import save_overlay_pdf


def run_comparison_pipeline(
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
    *,
    on_stage: Callable[[str], None] | None = None,
) -> CompareResponse:
    def report_stage(stage: str) -> None:
        if on_stage is not None:
            on_stage(stage)

    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)
    debug_run_id = uuid4().hex[:8]

    report_stage(STAGE_LOADING_DRAWINGS)
    drawing_a_image_pil, drawing_a_page = load_image_with_page_info(drawing_a_path)
    drawing_a_image = _pillow_to_bgr_array(drawing_a_image_pil)
    drawing_b_image = _pillow_to_bgr_array(load_image(drawing_b_path))

    save_debug_frame("01_drawing_a", drawing_a_image, run_id=debug_run_id)
    save_debug_frame("02_drawing_b", drawing_b_image, run_id=debug_run_id)

    try:
        report_stage(STAGE_ALIGNING_SHEETS)
        aligned_drawing_b, alignment_metadata = align_drawing_b_to_a(
            drawing_a_image,
            drawing_b_image,
            max_features=max_features_for_image(drawing_a_image),
            ecc_refinement=use_ecc_refinement_for_images(
                drawing_a_image,
                drawing_b_image,
            ),
        )
        save_debug_frame("03_aligned_b", aligned_drawing_b, run_id=debug_run_id)

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
        alignment_dpi = drawing_a_page.raster_dpi
        output_dpi = choose_output_dpi(
            comparison_bbox.width,
            comparison_bbox.height,
            alignment_dpi=alignment_dpi,
            preferred_dpi=PDF_DPI,
            max_pixels=MAX_IMAGE_PIXELS,
            max_dimension=MAX_IMAGE_DIMENSION,
        )
        report_stage(STAGE_PREPARING_COMPARISON)
        drawing_a_crop, aligned_drawing_b_crop = _build_comparison_crops(
            drawing_a_path,
            drawing_b_path,
            drawing_a_image,
            drawing_b_image,
            aligned_drawing_b,
            comparison_bbox,
            alignment_metadata=alignment_metadata,
            alignment_dpi=alignment_dpi,
            output_dpi=output_dpi,
        )
        aligned_drawing_b_crop = refine_crop_alignment(
            drawing_a_crop,
            aligned_drawing_b_crop,
        )
        save_debug_frame("04_drawing_a_crop", drawing_a_crop, run_id=debug_run_id)
        save_debug_frame("05_drawing_b_crop", aligned_drawing_b_crop, run_id=debug_run_id)

        report_stage(STAGE_BUILDING_OVERLAY)
        overlay_map, overlay_stats = render_coordination_overlay(
            drawing_a_crop,
            aligned_drawing_b_crop,
            drawing_a_name=drawing_a_name,
            drawing_b_name=drawing_b_name,
            low_confidence=alignment_confidence.status == "marginal",
            include_footer=False,
        )
        save_debug_frame("06_overlay_map", overlay_map, run_id=debug_run_id)

        crop_pixel_count = int(comparison_bbox.width * comparison_bbox.height)
        validate_overlay_stats(overlay_stats, crop_pixel_count=crop_pixel_count)

        rendered_image = append_coordination_footer(
            overlay_map,
            drawing_a_name=drawing_a_name,
            drawing_b_name=drawing_b_name,
            low_confidence=alignment_confidence.status == "marginal",
        )

        report_stage(STAGE_SAVING_RESULTS)
        output_id = uuid4().hex
        output_filename = f"comparison-{output_id}.png"
        pdf_filename = f"comparison-{output_id}.pdf"
        output_path = OUTPUT_DIR / output_filename
        pdf_path = OUTPUT_DIR / pdf_filename

        if not cv2.imwrite(str(output_path), rendered_image):
            raise ValueError("Failed to save comparison image.")

        save_overlay_pdf(
            pdf_path,
            overlay_map,
            page_width_pt=drawing_a_page.page_width_pt,
            page_height_pt=drawing_a_page.page_height_pt,
            raster_dpi=output_dpi,
            comparison_bbox=comparison_bbox,
            alignment_dpi=alignment_dpi,
            layout="crop",
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
                    "mode": "crop",
                    "width_pt": drawing_a_page.page_width_pt,
                    "height_pt": drawing_a_page.page_height_pt,
                    "raster_dpi": output_dpi,
                },
            },
        )
    finally:
        del drawing_a_image
        del drawing_b_image
        if "aligned_drawing_b" in locals():
            del aligned_drawing_b
        gc.collect()


def _build_comparison_crops(
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_image: np.ndarray,
    drawing_b_image: np.ndarray,
    aligned_drawing_b: np.ndarray,
    comparison_bbox,
    *,
    alignment_metadata: AlignmentMetadata,
    alignment_dpi: int,
    output_dpi: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Build comparison crops, re-rasterizing from PDF when output DPI is higher."""
    if output_dpi <= alignment_dpi:
        return (
            crop_image(drawing_a_image, comparison_bbox),
            crop_image(aligned_drawing_b, comparison_bbox),
        )

    scale = output_dpi / alignment_dpi
    drawing_a_crop = _pillow_to_bgr_array(
        rasterize_pdf_bbox(
            drawing_a_path,
            comparison_bbox,
            source_dpi=alignment_dpi,
            target_dpi=output_dpi,
        )
    )

    homography = np.array(alignment_metadata.homography, dtype=np.float64)
    scaled_homography = scale_homography(homography, scale)
    output_size = (
        int(round(drawing_a_image.shape[1] * scale)),
        int(round(drawing_a_image.shape[0] * scale)),
    )
    drawing_b_full_bbox = BoundingBox(
        x=0,
        y=0,
        width=int(drawing_b_image.shape[1]),
        height=int(drawing_b_image.shape[0]),
    )
    drawing_b_highres = _pillow_to_bgr_array(
        rasterize_pdf_bbox(
            drawing_b_path,
            drawing_b_full_bbox,
            source_dpi=alignment_dpi,
            target_dpi=output_dpi,
        )
    )
    warped_drawing_b = warp_drawing_with_homography(
        drawing_b_highres,
        scaled_homography,
        output_size,
    )
    aligned_drawing_b_crop = crop_image(
        warped_drawing_b,
        scale_bbox(comparison_bbox, scale),
    )
    aligned_drawing_b_crop = _match_crop_size(aligned_drawing_b_crop, drawing_a_crop)

    return drawing_a_crop, aligned_drawing_b_crop


def _match_crop_size(crop: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Resize a crop when PDF raster rounding leaves a 1px size mismatch."""
    target_size = (reference.shape[1], reference.shape[0])
    if crop.shape[1] == target_size[0] and crop.shape[0] == target_size[1]:
        return crop
    return cv2.resize(crop, target_size, interpolation=cv2.INTER_CUBIC)


def _pillow_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb_image: Image.Image = image.convert("RGB")
    rgb_array = np.asarray(rgb_image, dtype=np.uint8)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
