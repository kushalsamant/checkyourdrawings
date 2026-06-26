import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.app.config import COMPARE_MAX_WORKERS, COMPARE_TIMEOUT_SECONDS, PLATFORM_DATABASE_URL
from backend.app.database import _get_engine
from backend.app.services.alignment import AlignmentError
from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.app.services.image_limits import ImageTooLargeError
from backend.app.services.job_queue import claim_next_job, get_job, mark_job_completed, mark_job_failed, update_job_stage
from backend.app.services.pdf_converter import FileConversionError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=COMPARE_MAX_WORKERS)
_worker_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None


def _run_job_sync(job) -> dict:
    job_id = job.id

    def on_stage(stage: str) -> None:
        from sqlalchemy.orm import sessionmaker

        session_factory = sessionmaker(bind=_get_engine())
        db = session_factory()
        try:
            current = get_job(db, job_id)
            if current is not None:
                update_job_stage(db, current, stage)
        finally:
            db.close()

    result = run_comparison_pipeline(
        Path(job.drawing_a_path),
        Path(job.drawing_b_path),
        job.drawing_a_name,
        job.drawing_b_name,
        on_stage=on_stage,
    )
    payload = result.model_dump(mode="json")

    from backend.app.services.bunny_storage import bunny_enabled, publish_comparison_outputs

    if bunny_enabled():
        from backend.app.config import OUTPUT_DIR

        output_id = Path(payload["image_path"]).stem.removeprefix("comparison-")
        image_name = Path(payload["image_path"]).name
        pdf_name = Path(payload["pdf_path"]).name
        image_path = OUTPUT_DIR / image_name
        pdf_path = OUTPUT_DIR / pdf_name
        image_url, pdf_url = publish_comparison_outputs(output_id, image_path, pdf_path)
        payload["image_path"] = image_url
        payload["pdf_path"] = pdf_url
        for local_file in (image_path, pdf_path):
            try:
                local_file.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to remove local output %s", local_file)

    return payload


def _remove_file(file_path: str | None) -> None:
    if not file_path:
        return
    path = Path(file_path)
    if not path.exists():
        return
    try:
        path.unlink()
    except OSError as exc:
        logger.warning("Failed to remove temporary file %s: %s", path, exc)


def _process_one_job() -> bool:
    if not PLATFORM_DATABASE_URL:
        return False

    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(bind=_get_engine())
    db = session_factory()
    job = None
    try:
        job = claim_next_job(db)
        if job is None:
            return False

        try:
            payload = _run_job_sync(job)
            mark_job_completed(db, job, payload)
            logger.info("Comparison job %s completed", job.id)
        except UnsupportedFileTypeError as exc:
            mark_job_failed(db, job, str(exc))
        except ImageTooLargeError as exc:
            mark_job_failed(db, job, str(exc))
        except (FileConversionError, AlignmentError, ValueError) as exc:
            mark_job_failed(db, job, str(exc))
        except Exception as exc:
            logger.exception("Comparison job %s failed", job.id)
            mark_job_failed(db, job, str(exc) if str(exc) else "Comparison failed. Try again.")
        finally:
            _remove_file(job.drawing_a_path)
            _remove_file(job.drawing_b_path)
        return True
    finally:
        db.close()


async def _worker_loop(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        try:
            processed = await asyncio.wait_for(
                loop.run_in_executor(_executor, _process_one_job),
                timeout=COMPARE_TIMEOUT_SECONDS + 30,
            )
            if not processed:
                await asyncio.sleep(1.0)
        except asyncio.TimeoutError:
            logger.error("Comparison worker timed out processing a job")
        except Exception:
            logger.exception("Comparison worker loop error")
            await asyncio.sleep(2.0)


async def start_worker() -> None:
    global _worker_task, _stop_event
    if not PLATFORM_DATABASE_URL:
        logger.warning("Job worker disabled: PLATFORM_DATABASE_URL is not configured")
        return
    if _worker_task is not None and not _worker_task.done():
        return

    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(_worker_loop(_stop_event))
    logger.info("Comparison job worker started")


async def stop_worker() -> None:
    global _worker_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _worker_task is not None:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            _worker_task.cancel()
        _worker_task = None
    _stop_event = None
