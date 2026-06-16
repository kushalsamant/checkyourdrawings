from PIL import Image

from backend.app.config import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS


class ImageTooLargeError(Exception):
    """Raised when a decoded image exceeds configured pixel or dimension limits."""


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
