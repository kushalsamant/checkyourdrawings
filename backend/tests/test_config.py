import pytest

from backend.app.config import Settings, _DEFAULT_CORS_ORIGINS


class TestCorsOriginsSettings:
    def test_comma_separated_env_splits_into_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CYD_CORS_ORIGINS",
            "https://a.com,https://b.com",
        )
        settings = Settings()
        assert settings.cors_origins_list == ["https://a.com", "https://b.com"]

    def test_default_localhost_origins_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CYD_CORS_ORIGINS", raising=False)
        settings = Settings()
        assert settings.cors_origins == _DEFAULT_CORS_ORIGINS
        assert len(settings.cors_origins_list) == 4

    def test_whitespace_and_empty_segments_are_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CYD_CORS_ORIGINS",
            " https://a.com , , https://b.com ",
        )
        settings = Settings()
        assert settings.cors_origins_list == ["https://a.com", "https://b.com"]
