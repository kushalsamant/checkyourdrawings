import numpy as np

from backend.app.services.watermark import WATERMARK_TEXT, apply_watermark


def test_apply_watermark_changes_pixels() -> None:
    image = np.full((200, 300, 3), 255, dtype=np.uint8)
    watermarked = apply_watermark(image)

    assert watermarked.shape == image.shape
    assert not np.array_equal(watermarked, image)


def test_apply_watermark_uses_expected_text_constant() -> None:
    assert WATERMARK_TEXT == "checkyourdrawings.kvshvl.in"
