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
    MAX_FILE_SIZE_MB,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    UPLOAD_DIR,
)
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import AlignmentError, align_revision_to_reference
from backend.app.services.differencer import DifferenceError, detect_differences
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.output_cleanup import prune_old_outputs
from backend.app.services.pdf_converter import (
    FileConversionError,
    UnsupportedFileTypeError,
    load_image,
)
from backend.app.services.renderer import render_comparison_image

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])
_executor = ThreadPoolExecutor(max_workers=2)
_UPLOAD_CHUNK_SIZE = 1024 * 1024


@router.post("/compare", status_code=status.HTTP_200_OK, response_model=CompareResponse)
async def compare_drawings(revision_a: UploadFile, revision_b: UploadFile) -> CompareResponse:
    saved_revision_a: Path | None = None
    saved_revision_b: Path | None = None
    started_at = time.perf_counter()

    try:
        saved_revision_a = await _save_validated_upload(revision_a)
        saved_revision_b = await _save_validated_upload(revision_b)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor,
            _run_comparison_pipeline,
            saved_revision_a,
            saved_revision_b,
        )

        elapsed = time.perf_counter() - started_at
        logger.info("Comparison completed in %.2fs", elapsed)
        return result
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except ImageTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except (FileConversionError, AlignmentError, DifferenceError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _remove_file(saved_revision_a)
        _remove_file(saved_revision_b)


def _run_comparison_pipeline(revision_a_path: Path, revision_b_path: Path) -> CompareResponse:
    prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)

    reference_image = _pillow_to_bgr_array(load_image(revision_a_path))
    revision_image = _pillow_to_bgr_array(load_image(revision_b_path))

    aligned_image, alignment_metadata = align_revision_to_reference(
        reference_image,
        revision_image,
    )
    difference_result = detect_differences(reference_image, aligned_image)
    rendered_image = render_comparison_image(aligned_image, difference_result)

    output_filename: str = f"comparison-{uuid4().hex}.png"
    output_path: Path = OUTPUT_DIR / output_filename
    if not cv2.imwrite(str(output_path), rendered_image):
        raise ValueError("Failed to save comparison image.")

    return CompareResponse.from_pipeline_result(
        image_path=f"/outputs/{output_filename}",
        metadata={
            "alignment": asdict(alignment_metadata),
            "differences": asdict(difference_result),
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
