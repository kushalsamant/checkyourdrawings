import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.app.auth.deps import get_current_user
from backend.app.config import (
    ALLOWED_EXTENSIONS,
    COMPARE_MAX_WORKERS,
    COMPARE_TIMEOUT_SECONDS,
    MAX_FILE_SIZE_MB,
    UPLOAD_DIR,
)
from backend.app.schemas.compare import CompareResponse
from backend.app.services.alignment import AlignmentError
from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.pdf_converter import (
    FileConversionError,
    UnsupportedFileTypeError,
)
from backend.app.services.rate_limiter import rate_limit_compare

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])
_compare_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=COMPARE_MAX_WORKERS)
_UPLOAD_CHUNK_SIZE = 1024 * 1024
_COMPARE_BUSY_MESSAGE = "Another comparison is in progress. Try again in a moment."
_PDF_MAGIC = b"%PDF-"


@router.post(
    "/compare",
    status_code=status.HTTP_200_OK,
    response_model=CompareResponse,
    dependencies=[Depends(rate_limit_compare)],
)
async def compare_drawings(
    drawing_a: UploadFile | None = None,
    drawing_b: UploadFile | None = None,
    _user: object | None = Depends(get_current_user),
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
                    run_comparison_pipeline,
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
        _compare_lock.release()
        _remove_file(saved_drawing_a)
        _remove_file(saved_drawing_b)


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
    header: bytes = b""

    with saved_path.open("wb") as output_file:
        while True:
            chunk = await upload.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            if not header:
                header = chunk[:1024]
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

    if _PDF_MAGIC not in header:
        _remove_file(saved_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid PDF.",
        )

    return saved_path


def _remove_file(file_path: Path | None) -> None:
    if file_path is None or not file_path.exists():
        return

    try:
        file_path.unlink()
    except OSError as exc:
        logger.warning("Failed to remove temporary file %s: %s", file_path, exc)
