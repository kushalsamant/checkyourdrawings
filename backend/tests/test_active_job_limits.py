from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.user import AuthenticatedUser
from backend.app.database import get_db
from backend.app.main import app
from backend.app.services.active_job_limits import active_job_limit_detail, max_active_jobs_for_user
from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image

ANON_SESSION = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"


@pytest.fixture
def compare_files() -> dict[str, tuple[str, bytes, str]]:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
    return {
        "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
        "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
    }


def test_max_active_jobs_by_tier() -> None:
    assert max_active_jobs_for_user(None) == 1
    free = AuthenticatedUser(
        email="free@example.com",
        name=None,
        google_id=None,
        paid=False,
        priority=False,
        tier="free",
    )
    pro = AuthenticatedUser(
        email="pro@example.com",
        name=None,
        google_id=None,
        paid=True,
        priority=True,
        tier="monthly",
    )
    assert max_active_jobs_for_user(free) == 1
    assert max_active_jobs_for_user(pro) == 10


def test_active_job_limit_detail() -> None:
    assert "running" in active_job_limit_detail(1).lower()
    assert "10" in active_job_limit_detail(10)


def test_anonymous_active_job_limit_returns_409(compare_files: dict[str, tuple[str, bytes, str]]) -> None:
    mock_db = MagicMock()

    def override_db():
        yield mock_db

    with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
        app.dependency_overrides[get_db] = override_db
        with patch("backend.app.routes.compare.count_active_jobs", return_value=1):
            with patch("backend.app.routes.compare.anonymous_allowance_exhausted", return_value=False):
                client = TestClient(app)
                response = client.post(
                    "/compare",
                    files={
                        "drawing_a": compare_files["drawing_a"],
                        "drawing_b": compare_files["drawing_b"],
                    },
                    headers={"X-Anon-Session": ANON_SESSION},
                )
        app.dependency_overrides.clear()

    assert response.status_code == 409
