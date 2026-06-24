from fastapi import HTTPException, status

from backend.app.auth.user import AuthenticatedUser
from backend.app.models.comparison_job import ComparisonJob


def assert_job_access(
    job: ComparisonJob,
    user: AuthenticatedUser | None,
    anon_session_id: str | None,
) -> None:
    if job.user_email:
        if user is None or user.email != job.user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this comparison job.",
            )
        return

    if job.anon_session_id:
        if anon_session_id is None or anon_session_id != job.anon_session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this comparison job.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this comparison job.",
    )
