import numpy as np

from backend.app.services.overlay_renderer import render_coordination_overlay
from backend.tests.fixtures.factory import (
    ContentScenario,
    bgr_array_from_image,
    make_reference_image,
    make_revision_image,
)


class TestOverlayRenderer:
    def test_identical_images_produce_green_overlay(self) -> None:
        image = bgr_array_from_image(make_reference_image())
        output, stats = render_coordination_overlay(
            image,
            image,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        assert output.shape[0] > image.shape[0]
        assert stats.green_pixels > 0
        assert stats.red_pixels == 0
        assert stats.blue_pixels == 0

    def test_addition_produces_blue_pixels(self) -> None:
        from backend.app.services.alignment import align_revision_to_reference

        reference = bgr_array_from_image(make_reference_image())
        revision = bgr_array_from_image(
            make_revision_image(ContentScenario.ADDITION_ONLY, make_reference_image()),
        )
        aligned, _ = align_revision_to_reference(reference, revision)

        _, stats = render_coordination_overlay(
            reference,
            aligned,
            drawing_a_name="a.pdf",
            drawing_b_name="b.pdf",
        )

        assert stats.blue_pixels > 0
