import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, status
from PIL import Image

from backend.app.config import (
    ALLOWED_EXTENSIONS,
    COMPARE_TIMEOUT_SECONDS,
    MAX_FILE_SIZE_MB,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    UPLOAD_DIR,
)
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import (
    AlignmentError,
    align_drawing_b_to_a,
    evaluate_alignment_confidence,
)
from backend.app.services.content_detection import (
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
)
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.overlay_renderer import render_coordination_overlay
from backend.app.services.pdf_converter import (
    FileConversionError,
    UnsupportedFileTypeError,
    load_image,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])
_executor = ThreadPoolExecutor(max_workers=2)
_UPLOAD_CHUNK_SIZE = 1024 * 1024


@router.post("/compare", status_code=status.HTTP_200_OK, response_model=CompareResponse)
async def compare_drawings(
    drawing_a: UploadFile | None = None,
    drawing_b: UploadFile | None = None,
) -> CompareResponse:
    if drawing_a is None or drawing_b is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both drawing_a and drawing_b uploads are required.",
        )

    saved_drawing_a: Path | None = None
    saved_drawing_b: Path | None = None
    started_at = time.perf_counter()

    try:
        saved_drawing_a = await _save_validated_upload(drawing_a)
        saved_drawing_b = await _save_validated_upload(drawing_b)

        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    _run_comparison_pipeline,
                    saved_drawing_a,
                    saved_drawing_b,
                    drawing_a.filename or saved_drawing_a.name,
                    drawing_b.filename or saved_drawing_b.name,
                ),
                timeout=COMPARE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Comparison timed out after {COMPARE_TIMEOUT_SECONDS} seconds. "
                    "Try smaller files or try again."
                ),
            ) from exc

        elapsed = time.perf_counter() - started_at
        logger.info("Comparison completed in %.2fs", elapsed)
        return result
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except (FileConversionError, AlignmentError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _remove_file(saved_drawing_a)
        _remove_file(saved_drawing_b)


def _run_comparison_pipeline(
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
) -> CompareResponse:
    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)

    drawing_a_image = _pillow_to_bgr_array(load_image(drawing_a_path))
    drawing_b_image = _pillow_to_bgr_array(load_image(drawing_b_path))

    aligned_drawing_b, alignment_metadata = align_drawing_b_to_a(
        drawing_a_image,
        drawing_b_image,
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

    comparison_bbox = drawing_a_bbox
    drawing_a_crop = crop_image(drawing_a_image, comparison_bbox)
    aligned_drawing_b_crop = crop_image(aligned_drawing_b, comparison_bbox)

    rendered_image, overlay_stats = render_coordination_overlay(
        drawing_a_crop,
        aligned_drawing_b_crop,
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        low_confidence=alignment_confidence.status == "marginal",
    )

    output_filename: str = f"comparison-{uuid4().hex}.png"
    output_path: Path = OUTPUT_DIR / output_filename
    if not cv2.imwrite(str(output_path), rendered_image):
        raise ValueError("Failed to save comparison image.")

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
        metadata={
            "alignment": asdict(alignment_metadata),
            "alignment_confidence": asdict(alignment_confidence),
            "content": {
                "drawing_a_bbox": asdict(drawing_a_bbox),
                "drawing_b_bbox": asdict(drawing_b_bbox),
                "overlap_bbox": asdict(overlap_bbox),
            },
            "overlay": asdict(overlay_stats),
            "differences": {
                "width": int(comparison_bbox.width),
                "height": int(comparison_bbox.height),
                "changed_pixel_count": changed_pixels,
                "changed_pixel_ratio": changed_pixels / total_pixels,
            },
        },
    )


async def _save_validated_upload(upload: UploadFile) -> Path:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    extension: str = Path(upload.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed: str = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{extension or '<none>'}'. Allowed types: {allowed}.",
        )

    max_bytes: int = MAX_FILE_SIZE_MB * 1024 * 1024
    saved_path: Path = UPLOAD_DIR / f"{uuid4().hex}{extension}"
    total_bytes = 0

    with saved_path.open("wb") as output_file:
        while True:
            chunk = await upload.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                output_file.close()
                _remove_file(saved_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the maximum size of {MAX_FILE_SIZE_MB} MB.",
                )
            output_file.write(chunk)

    if total_bytes == 0:
        _remove_file(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    return saved_path


def _pillow_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb_image: Image.Image = image.convert("RGB")
    rgb_array = np.asarray(rgb_image, dtype=np.uint8)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)


def _remove_file(file_path: Path | None) -> None:
    if file_path is None or not file_path.exists():
        return

    try:
        file_path.unlink()
    except OSError as exc:
        logger.warning("Failed to remove temporary file %s: %s", file_path, exc)
