import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, Form, HTTPException, UploadFile, status
from PIL import Image

from backend.app.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    UPLOAD_DIR,
)
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import (
    AlignmentError,
    align_revision_to_reference,
    evaluate_alignment_confidence,
)
from backend.app.services.content_detection import (
    compute_overlap_bbox,
    crop_image,
    detect_content_bbox,
)
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.overlay_renderer import BackgroundMode, render_coordination_overlay
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
    revision_a: UploadFile | None = None,
    revision_b: UploadFile | None = None,
    background_mode: Literal["light", "dark"] = Form("light"),
) -> CompareResponse:
    upload_a = drawing_a or revision_a
    upload_b = drawing_b or revision_b
    if upload_a is None or upload_b is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both drawing_a and drawing_b uploads are required.",
        )

    saved_drawing_a: Path | None = None
    saved_drawing_b: Path | None = None
    started_at = time.perf_counter()

    try:
        saved_drawing_a = await _save_validated_upload(upload_a)
        saved_drawing_b = await _save_validated_upload(upload_b)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor,
            _run_comparison_pipeline,
            saved_drawing_a,
            saved_drawing_b,
            upload_a.filename or saved_drawing_a.name,
            upload_b.filename or saved_drawing_b.name,
            background_mode,
        )

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
    background_mode: BackgroundMode,
) -> CompareResponse:
    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)

    reference_image = _pillow_to_bgr_array(load_image(drawing_a_path))
    revision_image = _pillow_to_bgr_array(load_image(drawing_b_path))

    aligned_image, alignment_metadata = align_revision_to_reference(
        reference_image,
        revision_image,
    )
    alignment_confidence = evaluate_alignment_confidence(alignment_metadata)

    reference_bbox = detect_content_bbox(reference_image)
    revision_bbox = detect_content_bbox(aligned_image)
    if compute_overlap_bbox(reference_bbox, revision_bbox) is None:
        raise AlignmentError(
            "Could not find enough overlapping drawing content between the two files. "
            "They may show different views or have incompatible framing."
        )

    comparison_bbox = reference_bbox
    reference_crop = crop_image(reference_image, comparison_bbox)
    aligned_crop = crop_image(aligned_image, comparison_bbox)

    rendered_image, overlay_stats = render_coordination_overlay(
        reference_crop,
        aligned_crop,
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        background_mode=background_mode,
        low_confidence=alignment_confidence.status == "marginal",
    )

    output_filename: str = f"comparison-{uuid4().hex}.png"
    output_path: Path = OUTPUT_DIR / output_filename
    if not cv2.imwrite(str(output_path), rendered_image):
        raise ValueError("Failed to save comparison image.")

    changed_pixels = (
        overlay_stats.red_pixels
        + overlay_stats.blue_pixels
        + overlay_stats.magenta_pixels
    )
    total_pixels = max(
        1,
        overlay_stats.red_pixels
        + overlay_stats.blue_pixels
        + overlay_stats.green_pixels
        + overlay_stats.magenta_pixels,
    )

    return CompareResponse.from_pipeline_result(
        image_path=f"/outputs/{output_filename}",
        metadata={
            "alignment": asdict(alignment_metadata),
            "alignment_confidence": asdict(alignment_confidence),
            "content": {
                "reference_bbox": asdict(reference_bbox),
                "revision_bbox": asdict(revision_bbox),
                "overlap_bbox": asdict(comparison_bbox),
            },
            "overlay": asdict(overlay_stats),
            "differences": {
                "width": int(comparison_bbox.width),
                "height": int(comparison_bbox.height),
                "regions": [],
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
