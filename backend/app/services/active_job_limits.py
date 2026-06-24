"""Throughput limits — active jobs only (pending + running).

Locked business model (all tiers: 100 MB per PDF):
- Anonymous: 1 active job; 5 lifetime successful comparisons then sign-in required
- Signed-in free: 1 active job; unlimited comparisons
- Pro: 10 active jobs; unlimited comparisons; queue priority

No daily caps, monthly caps, usage quotas, or tiered file sizes.
"""

from backend.app.auth.user import AuthenticatedUser
from backend.app.config import MAX_ANON_ACTIVE_JOBS, MAX_FREE_ACTIVE_JOBS, MAX_PRO_ACTIVE_JOBS


def max_active_jobs_for_user(user: AuthenticatedUser | None) -> int:
    if user is None:
        return MAX_ANON_ACTIVE_JOBS
    if user.paid:
        return MAX_PRO_ACTIVE_JOBS
    return MAX_FREE_ACTIVE_JOBS


def active_job_limit_detail(limit: int) -> str:
    if limit <= 1:
        return (
            "Another comparison is pending or in progress. "
            "Wait for it to finish before starting a new one."
        )
    return (
        f"You have reached the limit of {limit} active comparisons "
        f"(pending or in progress). Wait for one to finish before starting another."
    )
