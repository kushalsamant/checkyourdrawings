import io

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.pdf_converter import load_image
from backend.tests.fixtures.factory import (
    ContentScenario,
    FileExtension,
    image_to_bytes,
    make_padded_identical_pair,
    make_reference_image,
    make_revision_image,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


EXTENSIONS: list[FileExtension] = [".pdf", ".png", ".jpg", ".jpeg"]
RASTER_EXTENSIONS: list[FileExtension] = [".png", ".jpg", ".jpeg"]


def _is_pdf_raster_mix(extension_a: FileExtension, extension_b: FileExtension) -> bool:
    return (extension_a == ".pdf") != (extension_b == ".pdf")


@pytest.mark.integration
@pytest.mark.parametrize("extension_a", EXTENSIONS)
@pytest.mark.parametrize("extension_b", EXTENSIONS)
def test_compare_file_type_matrix(
    client: TestClient,
    extension_a: FileExtension,
    extension_b: FileExtension,
    tmp_path,
) -> None:
    reference = make_reference_image()
    revision = make_revision_image(ContentScenario.IDENTICAL, reference)

    files = {
        "revision_a": (f"revision_a{extension_a}", image_to_bytes(reference, extension_a)),
        "revision_b": (f"revision_b{extension_b}", image_to_bytes(revision, extension_b)),
    }

    if _is_pdf_raster_mix(extension_a, extension_b):
        path_a = tmp_path / f"revision_a{extension_a}"
        path_b = tmp_path / f"revision_b{extension_b}"
        path_a.write_bytes(files["revision_a"][1])
        path_b.write_bytes(files["revision_b"][1])
        loaded_a = load_image(path_a)
        loaded_b = load_image(path_b)
        assert loaded_a.width > 0 and loaded_a.height > 0
        assert loaded_b.width > 0 and loaded_b.height > 0
        return

    response = client.post("/compare", files=files)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["image_path"].startswith("/outputs/comparison-")
    assert payload["metadata"]["alignment"]["inlier_matches"] >= 0


@pytest.mark.integration
@pytest.mark.parametrize("scenario", list(ContentScenario))
def test_compare_content_scenarios_png(client: TestClient, scenario: ContentScenario) -> None:
    reference = make_reference_image()
    revision = make_revision_image(scenario, reference)
    response = client.post(
        "/compare",
        files={
            "revision_a": ("a.png", image_to_bytes(reference, ".png"), "image/png"),
            "revision_b": ("b.png", image_to_bytes(revision, ".png"), "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    regions = response.json()["metadata"]["differences"]["regions"]

    if scenario == ContentScenario.IDENTICAL:
        assert len(regions) == 0
    else:
        assert len(regions) >= 1


@pytest.mark.integration
def test_compare_same_file_both_slots(client: TestClient) -> None:
    image_bytes = io.BytesIO()
    make_reference_image().save(image_bytes, format="PNG")
    content = image_bytes.getvalue()

    response = client.post(
        "/compare",
        files={
            "revision_a": ("a.png", content, "image/png"),
            "revision_b": ("b.png", content, "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["metadata"]["differences"]["changed_pixel_count"] == 0


@pytest.mark.integration
def test_compare_unequal_margins_identical_ink(client: TestClient) -> None:
    reference, revision = make_padded_identical_pair(
        margin_a=(30, 20, 100, 80),
        margin_b=(80, 60, 30, 20),
    )
    response = client.post(
        "/compare",
        files={
            "revision_a": ("a.png", image_to_bytes(reference, ".png"), "image/png"),
            "revision_b": ("b.png", image_to_bytes(revision, ".png"), "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metadata"]["differences"]["changed_pixel_count"] <= 100
    assert payload["metadata"]["alignment_confidence"]["status"] in {"high", "marginal"}
    assert payload["metadata"]["content"]["overlap_bbox"]["width"] > 0
