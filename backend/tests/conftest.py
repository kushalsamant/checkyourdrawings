import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Tests import `backend.app...`; ensure the repository root is importable in CI.
REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root = str(REPO_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


@pytest.fixture(autouse=True)
def reset_compare_lock() -> None:
    from backend.app.routes import compare as compare_route
    from backend.app.services import rate_limiter

    rate_limiter.reset()
    if compare_route._compare_lock.locked():
        compare_route._compare_lock.release()
    yield
    rate_limiter.reset()
    if compare_route._compare_lock.locked():
        compare_route._compare_lock.release()


@pytest.fixture
def client() -> TestClient:
    from backend.app.main import app

    return TestClient(app)
