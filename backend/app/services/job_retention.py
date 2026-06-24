import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.comparison_job import ComparisonJob
from backend.app.services.bunny_storage import bunny_enabled, delete_file

logger = logging.getLogger(__name__)


def _bunny_key_from_result_path(path: str) -> str | None:
    filename = Path(path.split("?")[0]).name
    if filename.startswith("comparison-") and filename.endswith((".png", ".pdf")):
        return filename
    return None


def _delete_bunny_artifacts_from_result(result: dict | None) -> None:
    if not result or not bunny_enabled():
        return
    for key in ("image_path", "pdf_path"):
        value = result.get(key)
        if isinstance(value, str):
            bunny_key = _bunny_key_from_result_path(value)
            if bunny_key:
                delete_file(bunny_key)


def prune_old_jobs(db: Session, *, max_age_hours: int) -> int:
    """Delete completed/failed comparison jobs older than the retention window."""
    if max_age_hours <= 0:
        return 0

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=max_age_hours)
    jobs = (
        db.query(ComparisonJob)
        .filter(
            ComparisonJob.status.in_(("completed", "failed")),
            ComparisonJob.completed_at.isnot(None),
            ComparisonJob.completed_at < cutoff,
        )
        .all()
    )

    removed_count = 0
    for job in jobs:
        _delete_bunny_artifacts_from_result(job.result)
        db.delete(job)
        removed_count += 1

    if removed_count:
        db.commit()
        logger.info("Pruned %d expired comparison job(s).", removed_count)

    return removed_count
