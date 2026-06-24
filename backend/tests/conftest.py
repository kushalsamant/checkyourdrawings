import os
import sys
from pathlib import Path
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_REQUIRED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

# Tests import `backend.app...`; ensure the repository root is importable in CI.
REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root = str(REPO_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

ANON_SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ANON_SESSION_HEADERS = {"X-Anon-Session": ANON_SESSION_ID}


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


@pytest.fixture
def compare_route_context(client: TestClient) -> Iterator[MagicMock]:
    """Mock Postgres + allowance/active-job gates so POST /compare reaches validation/enqueue."""
    from backend.app.database import get_db
    from backend.app.main import app

    mock_db = MagicMock()

    def override_db() -> Iterator[MagicMock]:
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    with (
        patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"),
        patch("backend.app.routes.compare.count_active_jobs", return_value=0),
        patch("backend.app.routes.compare.anonymous_allowance_exhausted", return_value=False),
    ):
        yield mock_db
    app.dependency_overrides.pop(get_db, None)
