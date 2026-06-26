import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.auth.anon_session import get_anon_session_id
from backend.app.auth.deps import get_current_user
from backend.app.auth.job_access import assert_job_access
from backend.app.auth.user import AuthenticatedUser
from backend.app.config import (
    ALLOWED_EXTENSIONS,
    ANONYMOUS_ALLOWANCE_TOTAL,
    MAX_FILE_SIZE_MB,
    PLATFORM_DATABASE_URL,
    UPLOAD_DIR,
)
from backend.app.database import get_db
from backend.app.schemas.compare import (
    AllowanceResponse,
    CompareJobCreatedResponse,
    CompareJobStatusResponse,
    CompareResponse,
)
from backend.app.services.active_job_limits import active_job_limit_detail, max_active_jobs_for_user
from backend.app.services.anonymous_allowance import (
    anonymous_allowance_exhausted,
    remaining_anonymous_allowance,
)
from backend.app.services.job_queue import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    count_active_jobs,
    create_job,
    get_job,
)
from backend.app.services.rate_limiter import rate_limit_compare

logger = logging.getLogger(__name__)
router = APIRouter(tags=["comparison"])
_UPLOAD_CHUNK_SIZE = 1024 * 1024
_PDF_MAGIC = b"%PDF-"


def _require_db(db: Session | None) -> Session:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Comparison job database is not configured.",
        )
    return db


@router.get(
    "/allowance",
    status_code=status.HTTP_200_OK,
    response_model=AllowanceResponse,
)
def get_allowance(
    user: AuthenticatedUser | None = Depends(get_current_user),
    anon_session_id: str | None = Depends(get_anon_session_id),
    db: Session | None = Depends(get_db),
) -> AllowanceResponse:
    db = _require_db(db)

    if user is not None:
        tier = "pro" if user.paid else "free"
        return AllowanceResponse(
            tier=tier,
            remaining=None,
            total=None,
            requires_sign_in=False,
        )

    if anon_session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anonymous session identifier is required.",
        )

    remaining = remaining_anonymous_allowance(db, anon_session_id)
    return AllowanceResponse(
        tier="anonymous",
        remaining=remaining,
        total=ANONYMOUS_ALLOWANCE_TOTAL,
        requires_sign_in=remaining <= 0,
    )


@router.post(
    "/compare",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CompareJobCreatedResponse,
    dependencies=[Depends(rate_limit_compare)],
)
async def compare_drawings(
    drawing_a: UploadFile | None = None,
    drawing_b: UploadFile | None = None,
    user: AuthenticatedUser | None = Depends(get_current_user),
    anon_session_id: str | None = Depends(get_anon_session_id),
    db: Session | None = Depends(get_db),
) -> CompareJobCreatedResponse:
    if drawing_a is None or drawing_b is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both drawing_a and drawing_b uploads are required.",
        )

    if not PLATFORM_DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Comparison job database is not configured.",
        )

    db = _require_db(db)

    if user is None:
        if anon_session_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anonymous session identifier is required.",
            )
        if anonymous_allowance_exhausted(db, anon_session_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue.",
            )

    active_limit = max_active_jobs_for_user(user)
    if user is not None:
        active_count = count_active_jobs(db, user_email=user.email)
    else:
        active_count = count_active_jobs(db, anon_session_id=anon_session_id)
    if active_count >= active_limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=active_job_limit_detail(active_limit),
        )

    saved_drawing_a: Path | None = None
    saved_drawing_b: Path | None = None

    try:
        saved_drawing_a = await _save_validated_upload(drawing_a)
        saved_drawing_b = await _save_validated_upload(drawing_b)

        priority = 1 if user is not None and user.priority else 0
        job = create_job(
            db,
            drawing_a_path=saved_drawing_a,
            drawing_b_path=saved_drawing_b,
            drawing_a_name=drawing_a.filename or saved_drawing_a.name,
            drawing_b_name=drawing_b.filename or saved_drawing_b.name,
            user_email=user.email if user is not None else None,
            anon_session_id=anon_session_id if user is None else None,
            platform_user_id=user.platform_user_id if user is not None else None,
            priority=priority,
        )
        return CompareJobCreatedResponse(job_id=str(job.id))
    except HTTPException:
        _remove_file(saved_drawing_a)
        _remove_file(saved_drawing_b)
        raise
    except Exception as exc:
        _remove_file(saved_drawing_a)
        _remove_file(saved_drawing_b)
        logger.exception("Failed to enqueue comparison job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue comparison job.",
        ) from exc


@router.get(
    "/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=CompareJobStatusResponse,
)
def get_compare_job(
    job_id: UUID,
    user: AuthenticatedUser | None = Depends(get_current_user),
    anon_session_id: str | None = Depends(get_anon_session_id),
    db: Session | None = Depends(get_db),
) -> CompareJobStatusResponse:
    db = _require_db(db)
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    assert_job_access(job, user, anon_session_id)

    result: CompareResponse | None = None
    if job.status == JOB_STATUS_COMPLETED and job.result is not None:
        result = CompareResponse.model_validate(job.result)

    return CompareJobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        stage=job.stage,
        result=result,
        error_message=job.error_message if job.status == JOB_STATUS_FAILED else None,
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
                    detail=f"File exceeds {MAX_FILE_SIZE_MB} MB.",
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
