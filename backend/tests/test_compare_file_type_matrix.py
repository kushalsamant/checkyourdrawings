import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.tests.fixtures.factory import (
    ContentScenario,
    image_to_bytes,
    make_padded_identical_pair,
    make_reference_image,
    make_revision_image,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.integration
def test_compare_identical_pdf(client: TestClient) -> None:
    reference = make_reference_image()
    revision = make_revision_image(ContentScenario.IDENTICAL, reference)

    response = client.post(
        "/compare",
        files={
            "drawing_a": ("drawing_a.pdf", image_to_bytes(reference, ".pdf"), "application/pdf"),
            "drawing_b": ("drawing_b.pdf", image_to_bytes(revision, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["image_path"].startswith("/outputs/comparison-")
    assert payload["metadata"]["overlay"]["green_pixels"] > 0
    assert payload["metadata"]["content"]["overlap_bbox"]["width"] > 0


@pytest.mark.integration
@pytest.mark.parametrize("scenario", list(ContentScenario))
def test_compare_content_scenarios_pdf(client: TestClient, scenario: ContentScenario) -> None:
    reference = make_reference_image()
    revision = make_revision_image(scenario, reference)
    response = client.post(
        "/compare",
        files={
            "drawing_a": ("a.pdf", image_to_bytes(reference, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(revision, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    overlay = payload["metadata"]["overlay"]
    if scenario == ContentScenario.IDENTICAL:
        assert overlay["green_pixels"] > 0
    else:
        assert overlay["red_pixels"] + overlay["blue_pixels"] + overlay["magenta_pixels"] > 0


@pytest.mark.integration
def test_compare_same_pdf_both_slots(client: TestClient) -> None:
    reference = make_reference_image()
    content = image_to_bytes(reference, ".pdf")

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
    assert overlay["red_pixels"] == 0
    assert overlay["blue_pixels"] == 0


@pytest.mark.integration
def test_compare_unequal_margins_identical_ink(client: TestClient) -> None:
    reference, revision = make_padded_identical_pair(
        margin_a=(30, 20, 100, 80),
        margin_b=(80, 60, 30, 20),
    )
    response = client.post(
        "/compare",
        files={
            "drawing_a": ("a.pdf", image_to_bytes(reference, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(revision, ".pdf"), "application/pdf"),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metadata"]["alignment_confidence"]["status"] in {"high", "marginal"}
    assert payload["metadata"]["content"]["overlap_bbox"]["width"] > 0
    assert payload["metadata"]["overlay"]["green_pixels"] > 0
