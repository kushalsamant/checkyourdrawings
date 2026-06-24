from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.config import ANONYMOUS_ALLOWANCE_TOTAL
from backend.app.models.anonymous_allowance import AnonymousAllowance


def get_successful_comparison_count(db: Session, anon_session_id: str) -> int:
    row = (
        db.query(AnonymousAllowance)
        .filter(AnonymousAllowance.anon_session_id == anon_session_id)
        .first()
    )
    if row is None:
        return 0
    return row.successful_comparisons


def remaining_anonymous_allowance(db: Session, anon_session_id: str) -> int:
    used = get_successful_comparison_count(db, anon_session_id)
    return max(0, ANONYMOUS_ALLOWANCE_TOTAL - used)


def anonymous_allowance_exhausted(db: Session, anon_session_id: str) -> bool:
    return remaining_anonymous_allowance(db, anon_session_id) <= 0


def record_anonymous_success(db: Session, anon_session_id: str) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    row = (
        db.query(AnonymousAllowance)
        .filter(AnonymousAllowance.anon_session_id == anon_session_id)
        .first()
    )
    if row is None:
        db.add(
            AnonymousAllowance(
                anon_session_id=anon_session_id,
                successful_comparisons=1,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        row.successful_comparisons += 1
        row.updated_at = now
        db.add(row)
    db.commit()
