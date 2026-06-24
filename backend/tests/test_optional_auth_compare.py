from unittest.mock import MagicMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from backend.app.auth.deps import get_current_user
from backend.app.auth.user import AuthenticatedUser
from backend.app.database import get_db
from backend.app.main import app
from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image


@pytest.fixture
def compare_files() -> dict[str, tuple[str, bytes, str]]:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
    return {
        "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
        "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
    }


class TestOptionalAuthCompare:
    def test_compare_enqueues_job_when_database_configured(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("backend.app.auth.deps.PLATFORM_JWT_SECRET", None)
        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "11111111-1111-1111-1111-111111111111"

        def mock_get_current_user() -> AuthenticatedUser:
            return AuthenticatedUser(
                email="test@example.com",
                name="Test User",
                google_id="google-123",
                paid=False,
                priority=False,
                tier="free",
            )

        def override_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            with patch("backend.app.routes.compare.create_job", return_value=mock_job):
                with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
                    app.dependency_overrides[get_db] = override_db
                    try:
                        response = client.post(
                            "/compare",
                            files=compare_files,
                            headers={"Authorization": "Bearer signed-in-token"},
                        )
                    finally:
                        app.dependency_overrides.pop(get_db, None)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 202
        assert response.json()["job_id"] == str(mock_job.id)

    def test_get_current_user_resolves_entitlements(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
        jwt_payload = {
            "email": "test@example.com",
            "sub": "google-123",
            "name": "Test User",
        }
        entitlements = {
            "app_id": "checkyourdrawings",
            "enabled": True,
            "paid": True,
            "priority": True,
            "tier": "monthly",
        }

        with patch("backend.app.auth.deps.PLATFORM_JWT_SECRET", "test-secret"):
            with patch("backend.app.auth.deps.decode_platform_jwt", return_value=jwt_payload):
                with patch(
                    "backend.app.auth.deps.fetch_entitlements",
                    return_value=entitlements,
                ):
                    user = get_current_user(credentials=credentials)

        assert user is not None
        assert user.email == "test@example.com"
        assert user.paid is True
        assert user.priority is True
        assert user.tier == "monthly"

    def test_compare_with_authenticated_user_when_db_configured(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
    ) -> None:
        def mock_get_current_user() -> AuthenticatedUser:
            return AuthenticatedUser(
                email="test@example.com",
                name="Test User",
                google_id="google-123",
                paid=False,
                priority=False,
                tier="trial",
            )

        mock_db = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "22222222-2222-2222-2222-222222222222"

        def override_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            with patch("backend.app.routes.compare.create_job", return_value=mock_job):
                with patch("backend.app.routes.compare.PLATFORM_DATABASE_URL", "postgresql://test"):
                    app.dependency_overrides[get_db] = override_db
                    try:
                        compare_response = client.post(
                            "/compare",
                            files=compare_files,
                            headers={"Authorization": "Bearer valid-token"},
                        )
                    finally:
                        app.dependency_overrides.pop(get_db, None)
        finally:
            app.dependency_overrides.clear()

        assert compare_response.status_code == 202
