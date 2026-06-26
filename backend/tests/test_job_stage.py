from pathlib import Path
from unittest.mock import MagicMock

from backend.app.services.compare_stages import STAGE_BUILDING_OVERLAY, STAGE_COMPLETED, STAGE_FAILED, STAGE_QUEUED
from backend.app.services.job_queue import JOB_STATUS_RUNNING, create_job, fail_interrupted_jobs, mark_job_completed, update_job_stage


def test_update_job_stage_persists() -> None:
    mock_db = MagicMock()
    mock_job = MagicMock()
    update_job_stage(mock_db, mock_job, STAGE_BUILDING_OVERLAY)
    assert mock_job.stage == STAGE_BUILDING_OVERLAY
    mock_db.add.assert_called_with(mock_job)
    mock_db.commit.assert_called()


def test_create_job_sets_queued_stage() -> None:
    mock_db = MagicMock()
    mock_db.refresh.side_effect = lambda job: job

    job = create_job(
        mock_db,
        drawing_a_path=Path("/tmp/a.pdf"),
        drawing_b_path=Path("/tmp/b.pdf"),
        drawing_a_name="a.pdf",
        drawing_b_name="b.pdf",
        user_email="user@example.com",
        anon_session_id=None,
        platform_user_id=1,
        priority=0,
    )
    assert job.stage == STAGE_QUEUED


def test_mark_job_completed_sets_completed_stage() -> None:
    mock_db = MagicMock()
    mock_job = MagicMock()
    mock_job.anon_session_id = None

    mark_job_completed(mock_db, mock_job, {"image_path": "/outputs/x.png", "pdf_path": "/outputs/x.pdf"})
    assert mock_job.stage == STAGE_COMPLETED


def test_fail_interrupted_jobs_marks_running_as_failed() -> None:
    mock_db = MagicMock()
    running_job = MagicMock()
    running_job.status = JOB_STATUS_RUNNING
    running_job.anon_session_id = None
    mock_db.query.return_value.filter.return_value.all.return_value = [running_job]

    count = fail_interrupted_jobs(mock_db)

    assert count == 1
    assert running_job.status == "failed"
    assert running_job.stage == STAGE_FAILED
    mock_db.commit.assert_called()
