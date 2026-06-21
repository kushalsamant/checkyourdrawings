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
def reset_rate_limiter() -> None:
    from backend.app.services import rate_limiter

    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client() -> TestClient:
    from backend.app.main import app

    return TestClient(app)
