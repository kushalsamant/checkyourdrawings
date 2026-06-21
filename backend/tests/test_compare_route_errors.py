import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.services.output_cleanup import prune_old_outputs


class TestCompareRouteErrors:
    def test_missing_filename(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "drawing_a": ("", b"data", "application/pdf"),
                "drawing_b": ("b.pdf", b"data", "application/pdf"),
            },
        )
        assert response.status_code in {400, 422}

    def test_unsupported_extension(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "drawing_a": ("a.gif", b"gif", "image/gif"),
                "drawing_b": ("b.png", b"png", "image/png"),
            },
        )
        assert response.status_code == 415

    def test_empty_file(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "drawing_a": ("a.pdf", b"", "application/pdf"),
                "drawing_b": ("b.pdf", b"x", "application/pdf"),
            },
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_oversize_bytes(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("backend.app.routes.compare.MAX_FILE_SIZE_MB", 0)
        response = client.post(
            "/compare",
            files={
                "drawing_a": ("a.pdf", b"12", "application/pdf"),
                "drawing_b": ("b.pdf", b"12", "application/pdf"),
            },
        )
        assert response.status_code == 413

    def test_corrupt_pdf(self, client: TestClient) -> None:
        response = client.post(
            "/compare",
            files={
                "drawing_a": ("a.pdf", b"not-a-pdf", "application/pdf"),
                "drawing_b": ("b.pdf", b"not-a-pdf", "application/pdf"),
            },
        )
        assert response.status_code == 400

    def test_success_response_shape(self, client: TestClient) -> None:
        from backend.tests.fixtures.factory import image_to_bytes, make_drawing_a_image

        content = image_to_bytes(make_drawing_a_image(), ".pdf")

        response = client.post(
            "/compare",
            files={
                "drawing_a": ("a.pdf", content, "application/pdf"),
                "drawing_b": ("b.pdf", content, "application/pdf"),
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "image_path" in payload
        assert "pdf_path" in payload
        assert payload["pdf_path"].endswith(".pdf")
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
        assert "comparison_bbox" in payload["metadata"]["content"]
        assert "output_page" in payload["metadata"]


class TestOutputCleanup:
    def test_prune_old_outputs(self, tmp_path: Path) -> None:
        old_png = tmp_path / "comparison-old.png"
        new_png = tmp_path / "comparison-new.png"
        old_pdf = tmp_path / "comparison-old.pdf"
        old_png.write_bytes(b"old")
        new_png.write_bytes(b"new")
        old_pdf.write_bytes(b"old-pdf")

        old_timestamp = time.time() - (48 * 3600)
        import os

        os.utime(old_png, (old_timestamp, old_timestamp))
        os.utime(old_pdf, (old_timestamp, old_timestamp))

        removed = prune_old_outputs(tmp_path, max_age_hours=24)
        assert removed == 2
        assert not old_png.exists()
        assert not old_pdf.exists()
        assert new_png.exists()

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
