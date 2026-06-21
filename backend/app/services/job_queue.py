import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.models.comparison_job import ComparisonJob

logger = logging.getLogger(__name__)

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"


def create_job(
    db: Session,
    *,
    drawing_a_path: Path,
    drawing_b_path: Path,
    drawing_a_name: str,
    drawing_b_name: str,
    user_email: str | None,
    priority: int,
) -> ComparisonJob:
    job = ComparisonJob(
        status=JOB_STATUS_PENDING,
        priority=priority,
        user_email=user_email,
        drawing_a_path=str(drawing_a_path),
        drawing_b_path=str(drawing_b_path),
        drawing_a_name=drawing_a_name,
        drawing_b_name=drawing_b_name,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: UUID) -> ComparisonJob | None:
    return db.query(ComparisonJob).filter(ComparisonJob.id == job_id).first()


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
    job.completed_at = now
    db.add(job)
    db.commit()


def mark_job_failed(db: Session, job: ComparisonJob, error_message: str) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    job.status = JOB_STATUS_FAILED
    job.error_message = error_message
    job.completed_at = now
    db.add(job)
    db.commit()
