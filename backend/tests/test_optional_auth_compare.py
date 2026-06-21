from unittest.mock import patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from backend.app.auth.deps import get_current_user
from backend.app.auth.user import AuthenticatedUser
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
    def test_compare_with_bearer_token_when_jwt_not_configured(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("backend.app.auth.deps.PLATFORM_JWT_SECRET", None)

        response = client.post(
            "/compare",
            files=compare_files,
            headers={"Authorization": "Bearer signed-in-token"},
        )

        assert response.status_code == 200
        assert response.json()["image_path"].startswith("/outputs/")

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

    def test_compare_with_authenticated_user(
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

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            compare_response = client.post(
                "/compare",
                files=compare_files,
                headers={"Authorization": "Bearer valid-token"},
            )
        finally:
            app.dependency_overrides.clear()

        assert compare_response.status_code == 200
