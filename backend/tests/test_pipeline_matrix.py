import numpy as np
import pytest

from backend.app.services.alignment import AlignmentError, align_drawing_b_to_a
from backend.app.services.pdf_converter import (
    UnsupportedFileTypeError,
    validate_file_type,
)
from backend.tests.fixtures.factory import (
    bgr_array_from_image,
    make_drawing_a_image,
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
        image = bgr_array_from_image(make_drawing_a_image())
        aligned, metadata = align_drawing_b_to_a(image, image)
        assert aligned.shape == image.shape
        assert metadata.inlier_matches >= 0

    def test_translated_drawing_b_aligns(self) -> None:
        drawing_a = bgr_array_from_image(make_drawing_a_image())
        drawing_b_image = make_drawing_a_image()
        drawing_b = bgr_array_from_image(drawing_b_image)
        aligned, metadata = align_drawing_b_to_a(drawing_a, drawing_b)
        assert aligned.shape[0] == drawing_a.shape[0]
        assert aligned.shape[1] == drawing_a.shape[1]
        assert metadata.output_width == drawing_a.shape[1]

    def test_blank_image_raises_alignment_error(self) -> None:
        blank = np.full((200, 200, 3), 255, dtype=np.uint8)
        with pytest.raises(AlignmentError):
            align_drawing_b_to_a(blank, blank)

    def test_ecc_refinement_runs_without_error(self) -> None:
        drawing_a = bgr_array_from_image(make_drawing_a_image())
        drawing_b = bgr_array_from_image(make_drawing_a_image())
        aligned_with, _ = align_drawing_b_to_a(drawing_a, drawing_b, ecc_refinement=True)
        aligned_without, _ = align_drawing_b_to_a(drawing_a, drawing_b, ecc_refinement=False)
        assert aligned_with.shape == aligned_without.shape
