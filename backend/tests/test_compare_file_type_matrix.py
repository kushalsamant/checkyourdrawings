import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.fixtures.factory import (
    ContentScenario,
    image_to_bytes,
    make_drawing_a_image,
    make_drawing_b_image,
    make_padded_identical_pair,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
def test_compare_identical_pdf(client: TestClient) -> None:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(ContentScenario.IDENTICAL, drawing_a)

    response = client.post(
        "/compare",
        files={
            "drawing_a": ("drawing_a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
            "drawing_b": ("drawing_b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["image_path"].startswith("/outputs/comparison-")
    assert payload["pdf_path"].startswith("/outputs/comparison-")
    assert payload["pdf_path"].endswith(".pdf")
    assert payload["metadata"]["overlay"]["green_pixels"] > 0
    assert payload["metadata"]["content"]["overlap_bbox"]["width"] > 0
    assert payload["metadata"]["content"]["comparison_bbox"]["width"] > 0


@pytest.mark.integration
@pytest.mark.parametrize("scenario", list(ContentScenario))
def test_compare_content_scenarios_pdf(client: TestClient, scenario: ContentScenario) -> None:
    drawing_a = make_drawing_a_image()
    drawing_b = make_drawing_b_image(scenario, drawing_a)
    response = client.post(
        "/compare",
        files={
            "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    overlay = payload["metadata"]["overlay"]
    if scenario == ContentScenario.IDENTICAL:
        assert overlay["green_pixels"] > 0
    else:
        assert overlay["orange_pixels"] + overlay["blue_pixels"] + overlay["red_pixels"] > 0


@pytest.mark.integration
def test_compare_same_pdf_both_slots(client: TestClient) -> None:
    drawing_a = make_drawing_a_image()
    content = image_to_bytes(drawing_a, ".pdf")

    response = client.post(
        "/compare",
        files={
            "drawing_a": ("a.pdf", content, "application/pdf"),
            "drawing_b": ("b.pdf", content, "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text
    overlay = response.json()["metadata"]["overlay"]
    assert overlay["green_pixels"] > 0
    assert overlay["orange_pixels"] == 0
    assert overlay["blue_pixels"] == 0


@pytest.mark.integration
def test_compare_unequal_margins_identical_ink(client: TestClient) -> None:
    drawing_a, drawing_b = make_padded_identical_pair(
        margin_a=(30, 20, 100, 80),
        margin_b=(80, 60, 30, 20),
    )
    response = client.post(
        "/compare",
        files={
            "drawing_a": ("a.pdf", image_to_bytes(drawing_a, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(drawing_b, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metadata"]["alignment_confidence"]["status"] in {"high", "marginal"}
    assert payload["metadata"]["content"]["overlap_bbox"]["width"] > 0
    assert payload["metadata"]["overlay"]["green_pixels"] > 0
