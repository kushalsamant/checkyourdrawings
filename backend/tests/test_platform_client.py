from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException, status

from backend.app.services import platform_client


class TestPlatformClient:
    def test_fetch_entitlements_returns_defaults_when_api_url_unset(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform_client, "PLATFORM_API_URL", None)

        result = platform_client.fetch_entitlements("token")

        assert result["paid"] is False
        assert result["tier"] == "trial"

    def test_fetch_entitlements_parses_success_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform_client, "PLATFORM_API_URL", "https://platform.example.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {
            "app_id": "checkyourdrawings",
            "enabled": True,
            "paid": True,
            "priority": True,
            "tier": "yearly",
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = platform_client.fetch_entitlements("token")

        assert result["paid"] is True
        mock_client.get.assert_called_once_with(
            "https://platform.example.com/entitlements",
            params={"app": "checkyourdrawings"},
            headers={"Authorization": "Bearer token"},
        )

    def test_fetch_entitlements_raises_on_unauthorized(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform_client, "PLATFORM_API_URL", "https://platform.example.com")
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_401_UNAUTHORIZED
        mock_response.is_success = False

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                platform_client.fetch_entitlements("token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_fetch_entitlements_raises_on_server_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(platform_client, "PLATFORM_API_URL", "https://platform.example.com")
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.is_success = False
        mock_response.text = "unavailable"

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                platform_client.fetch_entitlements("token")

        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
