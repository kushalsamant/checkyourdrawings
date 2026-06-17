import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.output_cleanup import prune_old_outputs


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestCompareRouteErrors:
    def test_missing_filename(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "revision_a": ("", b"data", "image/png"),
                "revision_b": ("b.png", b"data", "image/png"),
            },
        )
        assert response.status_code in {400, 422}

    def test_unsupported_extension(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "revision_a": ("a.gif", b"gif", "image/gif"),
                "revision_b": ("b.png", b"png", "image/png"),
            },
        )
        assert response.status_code == 415

    def test_empty_file(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "revision_a": ("a.png", b"", "image/png"),
                "revision_b": ("b.png", b"x", "image/png"),
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_oversize_bytes(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.app.routes.compare.MAX_FILE_SIZE_MB", 0)
        response = client.post(
            "/compare",
            files={
                "revision_a": ("a.png", b"12", "image/png"),
                "revision_b": ("b.png", b"12", "image/png"),
            },
        )
        assert response.status_code == 413

    def test_corrupt_image(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "revision_a": ("a.png", b"not-a-png", "image/png"),
                "revision_b": ("b.png", b"not-a-png", "image/png"),
            },
        )
        assert response.status_code == 400

    def test_success_response_shape(self, client: TestClient) -> None:
        from backend.tests.fixtures.factory import image_to_bytes, make_reference_image

        content = image_to_bytes(make_reference_image(), ".png")

        response = client.post(
            "/compare",
            files={
                "revision_a": ("a.png", content, "image/png"),
                "revision_b": ("b.png", content, "image/png"),
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "image_path" in payload
        assert "metadata" in payload
        assert "alignment" in payload["metadata"]
        assert "alignment_confidence" in payload["metadata"]
        assert "content" in payload["metadata"]
        assert "overlay" in payload["metadata"]
        assert "differences" in payload["metadata"]
        assert payload["metadata"]["alignment_confidence"]["status"] in {
            "high",
            "marginal",
            "failed",
        }
        assert "overlap_bbox" in payload["metadata"]["content"]


class TestOutputCleanup:
    def test_prune_old_outputs(self, tmp_path: Path) -> None:
        old_file = tmp_path / "comparison-old.png"
        new_file = tmp_path / "comparison-new.png"
        old_file.write_bytes(b"old")
        new_file.write_bytes(b"new")

        old_timestamp = time.time() - (48 * 3600)
        import os

        os.utime(old_file, (old_timestamp, old_timestamp))

        removed = prune_old_outputs(tmp_path, max_age_hours=24)
        assert removed == 1
        assert not old_file.exists()
        assert new_file.exists()

    def test_prune_disabled_when_zero_hours(self, tmp_path: Path) -> None:
        file_path = tmp_path / "comparison-old.png"
        file_path.write_bytes(b"x")
        assert prune_old_outputs(tmp_path, max_age_hours=0) == 0
        assert file_path.exists()


class TestHealthCheck:
    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in {"ok", "degraded"}
