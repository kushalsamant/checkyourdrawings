from unittest.mock import MagicMock, patch

from backend.app.services.job_retention import prune_old_jobs


def test_prune_old_jobs_deletes_expired_rows() -> None:
    mock_db = MagicMock()
    job = MagicMock()
    job.result = {
        "image_path": "https://cdn.example.com/comparison-old.png",
        "pdf_path": "https://cdn.example.com/comparison-old.pdf",
    }
    mock_db.query.return_value.filter.return_value.all.return_value = [job]

    with patch("backend.app.services.job_retention.bunny_enabled", return_value=False):
        removed = prune_old_jobs(mock_db, max_age_hours=24)

    assert removed == 1
    mock_db.delete.assert_called_once_with(job)
    mock_db.commit.assert_called_once()


def test_prune_old_jobs_noop_when_disabled() -> None:
    mock_db = MagicMock()
    assert prune_old_jobs(mock_db, max_age_hours=0) == 0
    mock_db.query.assert_not_called()
