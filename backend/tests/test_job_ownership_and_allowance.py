from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.deps import get_current_user
from backend.app.auth.user import AuthenticatedUser
from backend.app.database import get_db
from backend.app.main import app
from backend.app.models.comparison_job import ComparisonJob
from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image

ANON_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ANON_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
JOB_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def compare_files() -> dict[str, tuple[str, bytes, str]]:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
    return {
        "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
        "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
    }


def _completed_job(*, user_email: str | None = None, anon_session_id: str | None = None) -> ComparisonJob:
    job = ComparisonJob(
        id=JOB_ID,
        status="completed",
        priority=0,
        user_email=user_email,
        anon_session_id=anon_session_id,
        platform_user_id=None,
        drawing_a_path="/tmp/a.pdf",
        drawing_b_path="/tmp/b.pdf",
        drawing_a_name="a.pdf",
        drawing_b_name="b.pdf",
        result={
            "image_path": "/outputs/comparison-test.png",
            "pdf_path": "/outputs/comparison-test.pdf",
            "metadata": {
                "alignment": {
                    "keypoints_drawing_a": 1,
                    "keypoints_drawing_b": 1,
                    "raw_matches": 1,
                    "good_matches": 1,
                    "inlier_matches": 1,
                    "inlier_ratio": 1.0,
                    "homography": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                    "output_width": 100,
                    "output_height": 100,
                },
                "alignment_confidence": {"status": "high", "message": None},
                "content": {
                    "drawing_a_bbox": {"x": 0, "y": 0, "width": 10, "height": 10},
                    "drawing_b_bbox": {"x": 0, "y": 0, "width": 10, "height": 10},
                    "overlap_bbox": {"x": 0, "y": 0, "width": 10, "height": 10},
                    "comparison_bbox": {"x": 0, "y": 0, "width": 10, "height": 10},
                },
                "overlay": {
                    "orange_pixels": 0,
                    "blue_pixels": 0,
                    "green_pixels": 0,
                    "red_pixels": 0,
                },
                "differences": {
                    "width": 10,
                    "height": 10,
                    "changed_pixel_count": 0,
                    "changed_pixel_ratio": 0.0,
                },
                "output_page": {
                    "mode": "pdf",
                    "width_pt": 100.0,
                    "height_pt": 100.0,
                    "raster_dpi": 300,
                },
            },
        },
    )
    return job


class TestJobOwnershipRoutes:
    def test_get_job_forbidden_for_wrong_anon_session(self, client: TestClient) -> None:
        job = _completed_job(anon_session_id=ANON_A)
        mock_db = MagicMock()

        def override_db():
            yield mock_db

        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            with patch("backend.app.routes.compare.get_job", return_value=job):
                app.dependency_overrides[get_db] = override_db
                try:
                    response = client.get(
                        f"/jobs/{JOB_ID}",
                        headers={"X-Anon-Session": ANON_B},
                    )
                finally:
                    app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 403

    def test_get_job_allowed_for_matching_anon_session(self, client: TestClient) -> None:
        job = _completed_job(anon_session_id=ANON_A)
        mock_db = MagicMock()

        def override_db():
            yield mock_db

        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            with patch("backend.app.routes.compare.get_job", return_value=job):
                app.dependency_overrides[get_db] = override_db
                try:
                    response = client.get(
                        f"/jobs/{JOB_ID}",
                        headers={"X-Anon-Session": ANON_A},
                    )
                finally:
                    app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_get_job_forbidden_for_wrong_signed_in_user(self, client: TestClient) -> None:
        job = _completed_job(user_email="owner@example.com")
        mock_db = MagicMock()

        def mock_user() -> AuthenticatedUser:
            return AuthenticatedUser(
                email="other@example.com",
                name="Other",
                google_id="g-2",
                paid=False,
                priority=False,
                tier="free",
            )

        app.dependency_overrides[get_current_user] = mock_user
        try:
            def override_db():
                yield mock_db

            with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
                with patch("backend.app.routes.compare.get_job", return_value=job):
                    app.dependency_overrides[get_db] = override_db
                    try:
                        response = client.get(f"/jobs/{JOB_ID}")
                    finally:
                        app.dependency_overrides.pop(get_db, None)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403


class TestAnonymousAllowanceRoutes:
    def test_compare_requires_anon_session_when_unsigned(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
    ) -> None:
        mock_db = MagicMock()

        def override_db():
            yield mock_db

        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            app.dependency_overrides[get_db] = override_db
            try:
                response = client.post("/compare", files=compare_files)
            finally:
                app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 400
        assert "Anonymous session" in response.json()["detail"]

    def test_compare_returns_401_when_anonymous_allowance_exhausted(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
    ) -> None:
        mock_db = MagicMock()

        def override_db():
            yield mock_db

        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            with patch(
                "backend.app.routes.compare.anonymous_allowance_exhausted",
                return_value=True,
            ):
                app.dependency_overrides[get_db] = override_db
                try:
                    response = client.post(
                        "/compare",
                        files=compare_files,
                        headers={"X-Anon-Session": ANON_A},
                    )
                finally:
                    app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 401
        assert response.json()["detail"] == "Sign in to continue."

    def test_get_allowance_for_anonymous_session(self, client: TestClient) -> None:
        mock_db = MagicMock()

        def override_db():
            yield mock_db

        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            with patch(
                "backend.app.routes.compare.remaining_anonymous_allowance",
                return_value=3,
            ):
                app.dependency_overrides[get_db] = override_db
                try:
                    response = client.get(
                        "/allowance",
                        headers={"X-Anon-Session": ANON_A},
                    )
                finally:
                    app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 200
        payload = response.json()
        assert payload["tier"] == "anonymous"
        assert payload["remaining"] == 3
        assert payload["total"] == 5
        assert payload["requires_sign_in"] is False

    def test_get_allowance_for_signed_in_free_user(self, client: TestClient) -> None:
        mock_db = MagicMock()

        def mock_user() -> AuthenticatedUser:
            return AuthenticatedUser(
                email="user@example.com",
                name="User",
                google_id="g-1",
                paid=False,
                priority=False,
                tier="free",
            )

        app.dependency_overrides[get_current_user] = mock_user
        try:
            def override_db():
                yield mock_db

            with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
                app.dependency_overrides[get_db] = override_db
                try:
                    response = client.get("/allowance")
                finally:
                    app.dependency_overrides.pop(get_db, None)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        payload = response.json()
        assert payload["tier"] == "free"
        assert payload["remaining"] is None
        assert payload["requires_sign_in"] is False


class TestAnonSessionValidation:
    def test_invalid_anon_session_header_rejected(self, client: TestClient) -> None:
        with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
            response = client.get("/allowance", headers={"X-Anon-Session": "not-a-uuid"})

        assert response.status_code == 400
