"""Postgres-backed comparison job queue.

Claim order: priority DESC, created_at ASC (single global queue, serial worker).
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.models.comparison_job import ComparisonJob
from backend.app.services.compare_stages import STAGE_COMPLETED, STAGE_FAILED, STAGE_LOADING_DRAWINGS, STAGE_QUEUED

logger = logging.getLogger(__name__)

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


def count_active_jobs(
    db: Session,
    *,
    anon_session_id: str | None = None,
    user_email: str | None = None,
) -> int:
    query = db.query(ComparisonJob).filter(
        ComparisonJob.status.in_((JOB_STATUS_PENDING, JOB_STATUS_RUNNING))
    )
    if user_email is not None:
        query = query.filter(ComparisonJob.user_email == user_email)
    elif anon_session_id is not None:
        query = query.filter(ComparisonJob.anon_session_id == anon_session_id)
    else:
        return 0
    return query.count()


def create_job(
    db: Session,
    *,
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
    user_email: str | None,
    anon_session_id: str | None,
    platform_user_id: int | None,
    priority: int,
) -> ComparisonJob:
    job = ComparisonJob(
        status=JOB_STATUS_PENDING,
        priority=priority,
        user_email=user_email,
        anon_session_id=anon_session_id,
        platform_user_id=platform_user_id,
        drawing_a_path=str(drawing_a_path),
        drawing_b_path=str(drawing_b_path),
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        stage=STAGE_QUEUED,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: UUID) -> ComparisonJob | None:
    return db.query(ComparisonJob).filter(ComparisonJob.id == job_id).first()


def fail_interrupted_jobs(db: Session) -> int:
    """Fail orphaned running jobs after deploy or OOM restart.

    Upload paths live on ephemeral disk and do not survive a restart, so requeueing
    would only produce immediate file-not-found failures.
    """
    jobs = db.query(ComparisonJob).filter(ComparisonJob.status == JOB_STATUS_RUNNING).all()
    failed = 0
    for job in jobs:
        mark_job_failed(db, job, "Comparison interrupted by service restart. Try again.")
        failed += 1
    if failed:
        logger.info("Failed %d interrupted comparison job(s).", failed)
    return failed


def fail_jobs_with_missing_uploads(db: Session) -> int:
    """Fail queued jobs whose upload files are gone after a container restart."""
    jobs = db.query(ComparisonJob).filter(
        ComparisonJob.status.in_((JOB_STATUS_PENDING, JOB_STATUS_RUNNING))
    ).all()
    failed = 0
    for job in jobs:
        if Path(job.drawing_a_path).is_file() and Path(job.drawing_b_path).is_file():
            continue
        mark_job_failed(db, job, "Upload files expired after service restart. Try again.")
        failed += 1
    if failed:
        logger.info("Failed %d comparison job(s) with missing uploads.", failed)
    return failed


def requeue_interrupted_jobs(db: Session) -> int:
    """Deprecated alias — uploads do not survive Render restarts."""
    return fail_interrupted_jobs(db)


def claim_next_job(db: Session) -> ComparisonJob | None:
    row = db.execute(
        text(
            """
            select id
            from comparison_jobs
            where status = :pending
            order by priority desc, created_at asc
            for update skip locked
            limit 1
            """
        ),
        {"pending": JOB_STATUS_PENDING},
    ).first()
    if row is None:
        return None

    job_id = row[0]
    job = db.query(ComparisonJob).filter(ComparisonJob.id == job_id).first()
    if job is None:
        return None

    now = datetime.now(UTC).replace(tzinfo=None)
    job.status = JOB_STATUS_RUNNING
    job.stage = STAGE_LOADING_DRAWINGS
    job.started_at = now
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_completed(db: Session, job: ComparisonJob, result: dict) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    job.status = JOB_STATUS_COMPLETED
    job.result = result
    job.error_message = None
    job.stage = STAGE_COMPLETED
    job.completed_at = now
    db.add(job)
    db.commit()

    if job.anon_session_id:
        from backend.app.services.anonymous_allowance import record_anonymous_success

        record_anonymous_success(db, job.anon_session_id)


def mark_job_failed(db: Session, job: ComparisonJob, error_message: str) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    job.status = JOB_STATUS_FAILED
    job.error_message = error_message
    job.stage = STAGE_FAILED
    job.completed_at = now
    db.add(job)
    db.commit()


def update_job_stage(db: Session, job: ComparisonJob, stage: str) -> None:
    job.stage = stage
    db.add(job)
    db.commit()
