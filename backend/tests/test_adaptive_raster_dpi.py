import pytest

from backend.app.services.image_limits import ImageTooLargeError, choose_raster_dpi


class TestChooseRasterDpi:
    def test_a4_page_at_8m_budget_uses_200_dpi(self) -> None:
        dpi = choose_raster_dpi(
            842,
            1191,
            preferred_dpi=300,
            max_pixels=8_000_000,
        )
        assert dpi == 200

    def test_a4_page_at_4m_budget_uses_125_dpi(self) -> None:
        dpi = choose_raster_dpi(
            842,
            1191,
            preferred_dpi=300,
            max_pixels=4_000_000,
        )
        assert dpi == 125

    def test_small_page_keeps_preferred_dpi(self) -> None:
        dpi = choose_raster_dpi(
            400,
            300,
            preferred_dpi=300,
            max_pixels=8_000_000,
        )
        assert dpi == 300

    def test_raises_when_page_cannot_fit_even_at_minimum_dpi(self) -> None:
        with pytest.raises(ImageTooLargeError):
            choose_raster_dpi(
                20_000,
                20_000,
                preferred_dpi=300,
                max_pixels=8_000_000,
            )
