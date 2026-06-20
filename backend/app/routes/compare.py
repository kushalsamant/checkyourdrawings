import asyncio
import gc
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.auth.access import user_has_paid_access
from backend.app.auth.deps import get_current_user
from backend.app.config import (
    ALLOWED_EXTENSIONS,
    COMPARE_MAX_WORKERS,
    COMPARE_TIMEOUT_SECONDS,
    MAX_FILE_SIZE_MB,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    STORAGE_BYPASS,
    UPLOAD_DIR,
)
from backend.app.database import get_db
from backend.app.models.comparison import Comparison
from backend.app.models.user import User
from backend.app.schemas.compare import AccountStatusResponse, CompareResponse
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
)
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.overlay_renderer import render_coordination_overlay
from backend.app.services.pdf_converter import (
    FileConversionError,
    UnsupportedFileTypeError,
    load_image,
)
from backend.app.services.watermark import apply_watermark

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])
_compare_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=COMPARE_MAX_WORKERS)
_UPLOAD_CHUNK_SIZE = 1024 * 1024
_COMPARE_BUSY_MESSAGE = "Another comparison is in progress. Try again in a moment."


@router.get("/account", response_model=AccountStatusResponse)
def account_status(user: User | None = Depends(get_current_user)) -> AccountStatusResponse:
    return AccountStatusResponse(
        signed_in=user is not None,
        paid=user_has_paid_access(user),
        email=user.email if user is not None else None,
    )


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    response_model=CompareResponse,
)
async def compare_drawings(
    drawing_a: UploadFile | None = None,
    drawing_b: UploadFile | None = None,
    user: User | None = Depends(get_current_user),
    db: Session | None = Depends(get_db),
) -> CompareResponse:
    if drawing_a is None or drawing_b is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both drawing_a and drawing_b uploads are required.",
        )

    saved_drawing_a: Path | None = None
    saved_drawing_b: Path | None = None
    started_at = time.perf_counter()

    if not _compare_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_COMPARE_BUSY_MESSAGE,
        )

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

        drawing_a_name = drawing_a.filename or saved_drawing_a.name
        drawing_b_name = drawing_b.filename or saved_drawing_b.name
        paid = user_has_paid_access(user)

        if paid and not STORAGE_BYPASS:
            result = _store_comparison_in_cloud(
                result,
                user,
                db,
                drawing_a_name=drawing_a_name,
                drawing_b_name=drawing_b_name,
            )
        elif not paid:
            result = _apply_watermark_to_result(result)

        return result
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except (FileConversionError, AlignmentError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _compare_lock.release()
        _remove_file(saved_drawing_a)
        _remove_file(saved_drawing_b)


def _store_comparison_in_cloud(
    result: CompareResponse,
    user: User | None,
    db: Session | None,
    *,
    drawing_a_name: str,
    drawing_b_name: str,
) -> CompareResponse:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to compare drawings.",
        )

    local_filename = Path(result.image_path).name
    local_path = OUTPUT_DIR / local_filename
    if not local_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Comparison output file was not found for cloud upload.",
        )

    from backend.app.services.storage import upload_png_bytes

    comparison_id = uuid4()
    remote_path = f"{user.id}/{comparison_id}.png"
    png_bytes = local_path.read_bytes()
    image_url = upload_png_bytes(png_bytes, remote_path)

    if db is not None:
        metadata_payload = result.metadata.model_dump()
        metadata_payload["drawing_a_name"] = drawing_a_name
        metadata_payload["drawing_b_name"] = drawing_b_name
        db.add(
            Comparison(
                id=comparison_id,
                user_id=user.id,
                storage_path=remote_path,
                metadata_json=metadata_payload,
            )
        )
        db.commit()

    _remove_file(local_path)
    return CompareResponse(image_path=image_url, metadata=result.metadata)


def _apply_watermark_to_result(result: CompareResponse) -> CompareResponse:
    local_filename = Path(result.image_path).name
    local_path = OUTPUT_DIR / local_filename
    if not local_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Comparison output file was not found for watermarking.",
        )

    image = cv2.imread(str(local_path), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read comparison output for watermarking.",
        )

    watermarked = apply_watermark(image)
    if not cv2.imwrite(str(local_path), watermarked):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save watermarked comparison image.",
        )

    return result


def _run_comparison_pipeline(
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
) -> CompareResponse:
    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)

    drawing_a_image = _pillow_to_bgr_array(load_image(drawing_a_path))
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
    finally:
        del drawing_a_image
        del drawing_b_image
        if "aligned_drawing_b" in locals():
            del aligned_drawing_b
        gc.collect()


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
