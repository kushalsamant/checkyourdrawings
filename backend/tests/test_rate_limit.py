import pytest
from fastapi.testclient import TestClient

from backend.app.services import rate_limiter


class TestRateLimit:
    def test_compare_throttled_after_threshold(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rate_limiter, "ENABLED", True)
        monkeypatch.setattr(rate_limiter, "MAX_REQUESTS", 2)
        monkeypatch.setattr(rate_limiter, "WINDOW_SECONDS", 60)
        rate_limiter.reset()

        for _ in range(2):
            allowed = client.post("/compare", files={})
            assert allowed.status_code != 429

        throttled = client.post("/compare", files={})
        assert throttled.status_code == 429
        assert "retry-after" in {key.lower() for key in throttled.headers}

    def test_disabled_limiter_allows_many(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rate_limiter, "ENABLED", False)
        rate_limiter.reset()

        for _ in range(5):
            response = client.post("/compare", files={})
            assert response.status_code != 429
