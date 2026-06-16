import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.config import MAX_IMAGE_DIMENSION
from backend.app.main import app
from backend.app.services.image_limits import ImageTooLargeError, validate_image_dimensions


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestValidateImageDimensions:
    def test_accepts_image_within_limits(self) -> None:
        image = Image.new("RGB", (800, 600), color=(255, 255, 255))
        validate_image_dimensions(image)

    def test_rejects_over_dimension_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.image_limits.MAX_IMAGE_DIMENSION",
            100,
        )
        image = Image.new("RGB", (200, 50), color=(255, 255, 255))
        with pytest.raises(ImageTooLargeError, match="maximum side length"):
            validate_image_dimensions(image)

    def test_rejects_over_pixel_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.image_limits.MAX_IMAGE_PIXELS",
            1000,
        )
        image = Image.new("RGB", (50, 50), color=(255, 255, 255))
        with pytest.raises(ImageTooLargeError, match="pixel count"):
            validate_image_dimensions(image)

    @pytest.mark.parametrize(
        ("width", "height"),
        [
            (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
            (100, 100),
            (MAX_IMAGE_DIMENSION - 1, 100),
        ],
    )
    def test_boundary_sizes(self, width: int, height: int, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "backend.app.services.image_limits.MAX_IMAGE_PIXELS",
            MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION,
        )
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        if width * height <= MAX_IMAGE_DIMENSION * MAX_IMAGE_DIMENSION:
            validate_image_dimensions(image)
