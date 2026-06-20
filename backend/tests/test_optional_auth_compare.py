from unittest.mock import MagicMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from backend.app.auth.deps import get_current_user
from backend.app.main import app
from backend.app.models.user import User
from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def compare_files() -> dict[str, tuple[str, bytes, str]]:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
    return {
        "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
        "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
    }


class TestOptionalAuthCompare:
    def test_compare_with_bearer_token_when_no_db(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("backend.app.database.PLATFORM_DATABASE_URL", None)
        monkeypatch.setattr("backend.app.auth.deps.SUPABASE_URL", None)
        monkeypatch.setattr("backend.app.auth.deps.SUPABASE_JWT_SECRET", None)

        response = client.post(
            "/compare",
            files=compare_files,
            headers={"Authorization": "Bearer signed-in-token"},
        )

        assert response.status_code == 200
        assert response.json()["image_path"].startswith("/outputs/")

    def test_account_with_bearer_token_when_no_db(
        self,
        client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("backend.app.database.PLATFORM_DATABASE_URL", None)
        monkeypatch.setattr("backend.app.auth.deps.SUPABASE_URL", None)
        monkeypatch.setattr("backend.app.auth.deps.SUPABASE_JWT_SECRET", None)

        response = client.get(
            "/account",
            headers={"Authorization": "Bearer signed-in-token"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "signed_in": False,
            "paid": False,
            "email": None,
        }

    def test_get_current_user_provisions_user_when_db_available(self) -> None:
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
        jwt_payload = {
            "email": "test@example.com",
            "sub": "google-123",
            "name": "Test User",
        }

        with patch("backend.app.auth.deps.SUPABASE_URL", "https://example.supabase.co"):
            with patch("backend.app.auth.deps.decode_supabase_jwt", return_value=jwt_payload):
                user = get_current_user(credentials=credentials, db=mock_db)

        assert user is not None
        assert user.email == "test@example.com"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_compare_with_authenticated_user_when_db_configured(
        self,
        client: TestClient,
        compare_files: dict[str, tuple[str, bytes, str]],
    ) -> None:
        from backend.app.auth.deps import get_current_user

        def mock_get_current_user() -> User:
            return User(
                email="test@example.com",
                subscription_tier="trial",
                subscription_status="active",
                is_active=True,
            )

        app.dependency_overrides[get_current_user] = mock_get_current_user
        try:
            compare_response = client.post(
                "/compare",
                files=compare_files,
                headers={"Authorization": "Bearer valid-token"},
            )
            account_response = client.get(
                "/account",
                headers={"Authorization": "Bearer valid-token"},
            )
        finally:
            app.dependency_overrides.clear()

        assert compare_response.status_code == 200
        assert account_response.status_code == 200
        assert account_response.json() == {
            "signed_in": True,
            "paid": False,
            "email": "test@example.com",
        }
