import numpy as np

from backend.app.services.alignment import (
    max_features_for_image,
    use_ecc_refinement_for_images,
)


class TestAlignmentMemoryHelpers:
    def test_max_features_reduced_for_large_image(self) -> None:
        image = np.zeros((2000, 2000, 3), dtype=np.uint8)
        assert max_features_for_image(image) == 5_000

    def test_max_features_default_for_small_image(self) -> None:
        image = np.zeros((400, 300, 3), dtype=np.uint8)
        assert max_features_for_image(image) == 10_000

    def test_ecc_disabled_for_large_images(self) -> None:
        large = np.zeros((2000, 2000, 3), dtype=np.uint8)
        small = np.zeros((400, 300, 3), dtype=np.uint8)
        assert use_ecc_refinement_for_images(large, small) is False

    def test_ecc_enabled_for_small_images(self) -> None:
        small = np.zeros((400, 300, 3), dtype=np.uint8)
        assert use_ecc_refinement_for_images(small, small) is True
