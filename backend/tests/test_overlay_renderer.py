import numpy as np

from backend.app.services.overlay_renderer import (
    LIGHT_BLUE,
    LIGHT_GREEN,
    RED,
    ORANGE,
    render_coordination_overlay,
)
from backend.tests.fixtures.factory import (
    ContentScenario,
    bgr_array_from_image,
    make_drawing_a_image,
    make_drawing_b_image,
)


def _content_region(output: np.ndarray, source_height: int) -> np.ndarray:
    return output[:source_height]


def _count_color(content: np.ndarray, color: tuple[int, int, int]) -> int:
    color_array = np.array(color, dtype=np.uint8)
    return int(np.all(content == color_array, axis=2).sum())


class TestOverlayRenderer:
    def test_identical_images_render_green_pixels(self) -> None:
        image = bgr_array_from_image(make_drawing_a_image())
        output, stats = render_coordination_overlay(
            image,
            image,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, image.shape[0])
        assert _count_color(content, LIGHT_GREEN) == stats.green_pixels
        assert stats.green_pixels > 0
        assert stats.orange_pixels == 0
        assert stats.blue_pixels == 0
        assert _count_color(content, ORANGE) == 0
        assert _count_color(content, LIGHT_BLUE) == 0

    def test_a_only_ink_renders_orange_pixels(self) -> None:
        from backend.app.services.alignment import align_drawing_b_to_a

        drawing_a = bgr_array_from_image(make_drawing_a_image())
        drawing_b = bgr_array_from_image(
            make_drawing_b_image(ContentScenario.A_ONLY_INK, make_drawing_a_image()),
        )
        aligned, _ = align_drawing_b_to_a(drawing_a, drawing_b)

        output, stats = render_coordination_overlay(
            drawing_a,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, drawing_a.shape[0])
        assert stats.orange_pixels > 0
        assert _count_color(content, ORANGE) == stats.orange_pixels

    def test_b_only_ink_renders_blue_pixels(self) -> None:
        from backend.app.services.alignment import align_drawing_b_to_a

        drawing_a = bgr_array_from_image(make_drawing_a_image())
        drawing_b = bgr_array_from_image(
            make_drawing_b_image(ContentScenario.B_ONLY_INK, make_drawing_a_image()),
        )
        aligned, _ = align_drawing_b_to_a(drawing_a, drawing_b)

        output, stats = render_coordination_overlay(
            drawing_a,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, drawing_a.shape[0])
        assert stats.blue_pixels > 0
        assert _count_color(content, LIGHT_BLUE) == stats.blue_pixels

    def test_offset_alignment_renders_red_clash_pixels(self) -> None:
        drawing_a = bgr_array_from_image(make_drawing_a_image())
        aligned = np.full_like(drawing_a, 255)
        shift = 2
        height, width = drawing_a.shape[:2]
        aligned[shift:height, shift:width] = drawing_a[: height - shift, : width - shift]

        output, stats = render_coordination_overlay(
            drawing_a,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        content = _content_region(output, drawing_a.shape[0])
        assert stats.red_pixels > 0
        assert _count_color(content, RED) == stats.red_pixels
