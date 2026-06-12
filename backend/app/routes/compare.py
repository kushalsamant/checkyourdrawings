from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, status
from PIL import Image

from backend.app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, OUTPUT_DIR, UPLOAD_DIR
from backend.app.services.alignment import AlignmentError, align_revision_to_reference
from backend.app.services.differencer import DifferenceError, detect_differences
from backend.app.services.pdf_converter import (
    FileConversionError,
    UnsupportedFileTypeError,
    load_image,
)
from backend.app.services.renderer import render_comparison_image


router = APIRouter(tags=["comparison"])


@router.post("/compare", status_code=status.HTTP_200_OK)
async def compare_drawings(revision_a: UploadFile, revision_b: UploadFile) -> dict[str, object]:
    saved_revision_a: Path | None = None
    saved_revision_b: Path | None = None

    try:
        saved_revision_a = await _save_validated_upload(revision_a)
        saved_revision_b = await _save_validated_upload(revision_b)

        reference_image = _pillow_to_bgr_array(load_image(saved_revision_a))
        revision_image = _pillow_to_bgr_array(load_image(saved_revision_b))

        aligned_image, alignment_metadata = align_revision_to_reference(
            reference_image,
            revision_image,
        )
        difference_result = detect_differences(reference_image, aligned_image)
        rendered_image = render_comparison_image(aligned_image, difference_result)

        output_filename: str = f"comparison-{uuid4().hex}.png"
        output_path: Path = OUTPUT_DIR / output_filename
        if not cv2.imwrite(str(output_path), rendered_image):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save comparison image.",
            )

        return {
            "image_path": f"/outputs/{output_filename}",
            "metadata": {
                "alignment": asdict(alignment_metadata),
                "differences": asdict(difference_result),
            },
        }
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except (FileConversionError, AlignmentError, DifferenceError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        _remove_file(saved_revision_a)
        _remove_file(saved_revision_b)


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

    content: bytes = await upload.read()
    max_bytes: int = MAX_FILE_SIZE_MB * 1024 * 1024

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum size of {MAX_FILE_SIZE_MB} MB.",
        )

    saved_path: Path = UPLOAD_DIR / f"{uuid4().hex}{extension}"
    saved_path.write_bytes(content)
    return saved_path


def _pillow_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb_image: Image.Image = image.convert("RGB")
    rgb_array = np.asarray(rgb_image, dtype=np.uint8)
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)


def _remove_file(file_path: Path | None) -> None:
    if file_path is not None and file_path.exists():
        file_path.unlink()
