from PIL import Image

from backend.app.config import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS


class ImageTooLargeError(Exception):
    """Raised when a decoded image exceeds configured pixel or dimension limits."""


def choose_raster_dpi(
    page_width_pt: float,
    page_height_pt: float,
    *,
    preferred_dpi: int,
    max_pixels: int,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> int:
    """Pick the highest DPI (<= preferred) so the raster fits memory and decode limits."""
    if page_width_pt <= 0 or page_height_pt <= 0:
        raise ValueError("page dimensions must be positive.")

    if preferred_dpi <= 0:
        raise ValueError("preferred_dpi must be greater than zero.")

    candidates = _dpi_candidates(preferred_dpi)
    for dpi in candidates:
        width = int(page_width_pt / 72 * dpi)
        height = int(page_height_pt / 72 * dpi)
        pixel_count = width * height
        if (
            width <= max_dimension
            and height <= max_dimension
            and pixel_count <= max_pixels
            and pixel_count <= MAX_IMAGE_PIXELS
        ):
            return dpi

    raise ImageTooLargeError(
        f"PDF page {page_width_pt:.0f}x{page_height_pt:.0f} pt cannot be rasterized within "
        f"{max_pixels:,} pixels at any supported DPI down to {candidates[-1]}."
    )


def choose_output_dpi(
    crop_width_px: int,
    crop_height_px: int,
    *,
    alignment_dpi: int,
    preferred_dpi: int,
    max_pixels: int,
    max_dimension: int = MAX_IMAGE_DIMENSION,
) -> int:
    """Pick the highest DPI (>= alignment) so a comparison crop fits decode limits."""
    if crop_width_px <= 0 or crop_height_px <= 0:
        raise ValueError("crop dimensions must be positive.")

    if alignment_dpi <= 0:
        raise ValueError("alignment_dpi must be greater than zero.")

    if preferred_dpi <= 0:
        raise ValueError("preferred_dpi must be greater than zero.")

    best_dpi = alignment_dpi
    for dpi in _dpi_candidates(preferred_dpi):
        if dpi < alignment_dpi:
            continue

        scale = dpi / alignment_dpi
        width = int(crop_width_px * scale)
        height = int(crop_height_px * scale)
        pixel_count = width * height
        if (
            width <= max_dimension
            and height <= max_dimension
            and pixel_count <= max_pixels
            and pixel_count <= MAX_IMAGE_PIXELS
        ):
            best_dpi = dpi
            break

    return best_dpi


def _dpi_candidates(preferred_dpi: int) -> list[int]:
    standard_steps = (300, 250, 200, 175, 150, 125, 100, 72)
    candidates = [dpi for dpi in standard_steps if dpi <= preferred_dpi]
    if not candidates or candidates[0] != preferred_dpi:
        candidates = [preferred_dpi, *candidates]
    deduped: list[int] = []
    for dpi in candidates:
        if dpi > 0 and dpi not in deduped:
            deduped.append(dpi)
    return deduped


def validate_image_dimensions(image: Image.Image) -> None:
    """Reject images that exceed configured decode limits."""
    width, height = image.size
    pixel_count = width * height

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ImageTooLargeError(
            f"Image dimensions {width}x{height} exceed the maximum side length "
            f"of {MAX_IMAGE_DIMENSION} pixels."
        )

    if pixel_count > MAX_IMAGE_PIXELS:
        raise ImageTooLargeError(
            f"Image pixel count {pixel_count:,} exceeds the maximum of "
            f"{MAX_IMAGE_PIXELS:,} pixels."
        )
