import numpy as np
import pytest

from backend.app.services.alignment import AlignmentError, align_revision_to_reference
from backend.app.services.pdf_converter import (
    UnsupportedFileTypeError,
    validate_file_type,
)
from backend.tests.fixtures.factory import (
    bgr_array_from_image,
    make_reference_image,
)


class TestValidateFileType:
    @pytest.mark.parametrize("extension", [".pdf"])
    def test_allowed_extensions(self, extension: str, tmp_path) -> None:
        path = tmp_path / f"file{extension}"
        path.write_bytes(b"x")
        validate_file_type(path)

    @pytest.mark.parametrize("extension", [".png", ".jpg", ".jpeg", ".gif", ".dwg", ".txt", ".bmp", ""])
    def test_rejected_extensions(self, extension: str, tmp_path) -> None:
        name = f"file{extension}" if extension else "file"
        path = tmp_path / name
        path.write_bytes(b"x")
        with pytest.raises(UnsupportedFileTypeError):
            validate_file_type(path)


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
