from fastapi.testclient import TestClient


class TestSecurityHeaders:
    def test_health_response_has_security_headers(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert "max-age=" in response.headers["Strict-Transport-Security"]
