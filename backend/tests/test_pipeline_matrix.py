import numpy as np
import pytest

from backend.app.services.alignment import AlignmentError, align_revision_to_reference
from backend.app.services.differencer import detect_differences
from backend.app.services.pdf_converter import (
    UnsupportedFileTypeError,
    validate_file_type,
)
from backend.app.services.renderer import encode_comparison_png, render_comparison_image
from backend.tests.fixtures.factory import (
    ContentScenario,
    bgr_array_from_image,
    make_reference_image,
    make_revision_image,
)


class TestValidateFileType:
    @pytest.mark.parametrize("extension", [".pdf", ".png", ".jpg", ".jpeg", ".dwg"])
    def test_allowed_extensions(self, extension: str, tmp_path) -> None:
        path = tmp_path / f"file{extension}"
        path.write_bytes(b"x")
        validate_file_type(path)

    @pytest.mark.parametrize("extension", [".gif", ".txt", ".bmp", ""])
    def test_rejected_extensions(self, extension: str, tmp_path) -> None:
        name = f"file{extension}" if extension else "file"
        path = tmp_path / name
        path.write_bytes(b"x")
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_type(path)


class TestDifferencerScenarios:
    @pytest.mark.parametrize("scenario", list(ContentScenario))
    def test_detect_differences(self, scenario: ContentScenario) -> None:
        reference = bgr_array_from_image(make_reference_image())
        revision = bgr_array_from_image(make_revision_image(scenario, make_reference_image()))

        aligned, _ = align_revision_to_reference(reference, revision)
        result = detect_differences(reference, aligned)

        assert result.width == reference.shape[1]
        assert result.height == reference.shape[0]

        if scenario == ContentScenario.IDENTICAL:
            assert result.changed_pixel_count == 0
            assert len(result.regions) == 0
        else:
            assert result.changed_pixel_count > 0


class TestAlignmentScenarios:
    def test_identity_alignment(self) -> None:
        image = bgr_array_from_image(make_reference_image())
        aligned, metadata = align_revision_to_reference(image, image)
        assert aligned.shape == image.shape
        assert metadata.inlier_matches >= 0

    def test_translated_revision_aligns(self) -> None:
        reference = bgr_array_from_image(make_reference_image())
        revision_image = make_reference_image()
        revision = bgr_array_from_image(revision_image)
        aligned, metadata = align_revision_to_reference(reference, revision)
        assert aligned.shape[0] == reference.shape[0]
        assert aligned.shape[1] == reference.shape[1]
        assert metadata.output_width == reference.shape[1]

    def test_blank_image_raises_alignment_error(self) -> None:
        blank = np.full((200, 200, 3), 255, dtype=np.uint8)
        with pytest.raises(AlignmentError):
            align_revision_to_reference(blank, blank)


class TestRenderer:
    def test_render_and_encode(self) -> None:
        reference = bgr_array_from_image(make_reference_image())
        revision = bgr_array_from_image(make_revision_image(ContentScenario.ADDITION_ONLY, make_reference_image()))
        aligned, _ = align_revision_to_reference(reference, revision)
        differences = detect_differences(reference, aligned)
        rendered = render_comparison_image(aligned, differences)
        png_bytes = encode_comparison_png(rendered)
        assert png_bytes.startswith(b"\x89PNG")

    def test_render_zero_regions(self) -> None:
        image = bgr_array_from_image(make_reference_image())
        aligned, _ = align_revision_to_reference(image, image)
        differences = detect_differences(image, aligned)
        rendered = render_comparison_image(aligned, differences)
        assert rendered.shape == image.shape
