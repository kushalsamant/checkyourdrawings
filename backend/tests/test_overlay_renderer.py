import numpy as np

from backend.app.services.overlay_renderer import (
    LIGHT_BLUE,
    LIGHT_GREEN,
    LIGHT_MAGENTA,
    LIGHT_RED,
    render_coordination_overlay,
)
from backend.tests.fixtures.factory import (
    ContentScenario,
    bgr_array_from_image,
    make_reference_image,
    make_revision_image,
)


def _content_region(output: np.ndarray, source_height: int) -> np.ndarray:
    return output[:source_height]


def _count_color(content: np.ndarray, color: tuple[int, int, int]) -> int:
    color_array = np.array(color, dtype=np.uint8)
    return int(np.all(content == color_array, axis=2).sum())


class TestOverlayRenderer:
    def test_composite_identical_images_render_green_pixels(self) -> None:
        image = bgr_array_from_image(make_reference_image())
        output, stats = render_coordination_overlay(
            image,
            image,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, image.shape[0])
        assert _count_color(content, LIGHT_GREEN) == stats.green_pixels
        assert stats.green_pixels > 0
        assert stats.red_pixels == 0
        assert stats.blue_pixels == 0
        assert _count_color(content, LIGHT_RED) == 0
        assert _count_color(content, LIGHT_BLUE) == 0

    def test_diff_only_matches_composite_paint(self) -> None:
        image = bgr_array_from_image(make_reference_image())
        composite_output, _ = render_coordination_overlay(
            image,
            image,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
            overlay_mode="composite",
        )
        diff_output, _ = render_coordination_overlay(
            image,
            image,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
            overlay_mode="diff_only",
        )

        assert np.array_equal(
            _content_region(composite_output, image.shape[0]),
            _content_region(diff_output, image.shape[0]),
        )

    def test_addition_renders_blue_pixels(self) -> None:
        from backend.app.services.alignment import align_revision_to_reference

        reference = bgr_array_from_image(make_reference_image())
        revision = bgr_array_from_image(
            make_revision_image(ContentScenario.ADDITION_ONLY, make_reference_image()),
        )
        aligned, _ = align_revision_to_reference(reference, revision)

        output, stats = render_coordination_overlay(
            reference,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, reference.shape[0])
        assert stats.blue_pixels > 0
        assert _count_color(content, LIGHT_BLUE) == stats.blue_pixels

    def test_deletion_renders_red_pixels(self) -> None:
        from backend.app.services.alignment import align_revision_to_reference

        reference = bgr_array_from_image(make_reference_image())
        revision = bgr_array_from_image(
            make_revision_image(ContentScenario.DELETION_ONLY, make_reference_image()),
        )
        aligned, _ = align_revision_to_reference(reference, revision)

        output, stats = render_coordination_overlay(
            reference,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, reference.shape[0])
        assert stats.red_pixels > 0
        assert _count_color(content, LIGHT_RED) == stats.red_pixels

    def test_offset_alignment_renders_magenta_clash_pixels(self) -> None:
        reference = bgr_array_from_image(make_reference_image())
        aligned = np.full_like(reference, 255)
        shift = 2
        height, width = reference.shape[:2]
        aligned[shift:height, shift:width] = reference[: height - shift, : width - shift]

        output, stats = render_coordination_overlay(
            reference,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, reference.shape[0])
        assert stats.magenta_pixels > 0
        assert _count_color(content, LIGHT_MAGENTA) == stats.magenta_pixels
