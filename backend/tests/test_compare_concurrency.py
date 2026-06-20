from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routes import compare as compare_route
from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestCompareConcurrency:
    def test_compare_returns_503_when_lock_is_busy(self, client: TestClient) -> None:
        drawing_a = make_drawing_a_image()
        drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
        files = {
            "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
        }

        compare_route._compare_lock.acquire()
        try:
            response = client.post("/compare", files=files)
        finally:
            compare_route._compare_lock.release()

        assert response.status_code == 503
        assert "in progress" in response.json()["detail"].lower()

    def test_compare_releases_lock_after_success(self, client: TestClient) -> None:
        drawing_a = make_drawing_a_image()
        drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)
        files = {
            "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
        }

        first = client.post("/compare", files=files)
        second = client.post("/compare", files=files)

        assert first.status_code == 200
        assert second.status_code == 200
        assert not compare_route._compare_lock.locked()
