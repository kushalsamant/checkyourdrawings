import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import (
    CORS_ORIGINS,
    OUTPUT_DIR,
    OUTPUT_MAX_AGE_HOURS,
    UPLOAD_DIR,
    ensure_runtime_directories,
)
from backend.app.routes.compare import router as compare_router
from backend.app.services.output_cleanup import prune_old_outputs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_runtime_directories()
    removed = prune_old_outputs(OUTPUT_DIR, max_age_hours=OUTPUT_MAX_AGE_HOURS)
    logger.info("Application startup complete. Pruned %d expired output file(s).", removed)
    yield


app = FastAPI(
    title="Check Your Drawings API",
    description="Computer vision API for comparing drawing revisions.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compare_router)
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    return {
        "application": "Check Your Drawings",
        "status": "running",
    }


@app.get("/health", tags=["health"])
def health_check() -> dict[str, object]:
    issues: list[str] = []

    for directory in (UPLOAD_DIR, OUTPUT_DIR):
        if not directory.exists():
            issues.append(f"Missing directory: {directory.name}")
            continue

        probe_file = directory / ".health_probe"
        try:
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink()
        except OSError:
            issues.append(f"Directory not writable: {directory.name}")

    if issues:
        return {"status": "degraded", "issues": issues}

    return {"status": "ok", "upload_dir": str(UPLOAD_DIR), "output_dir": str(OUTPUT_DIR)}
