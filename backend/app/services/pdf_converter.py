import logging
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from backend.app.config import ALLOWED_EXTENSIONS, COMPARE_MAX_RASTER_PIXELS, PDF_DPI
from backend.app.services.content_detection import BoundingBox
from backend.app.services.image_limits import (
    ImageTooLargeError,
    choose_raster_dpi,
    validate_image_dimensions,
)

logger = logging.getLogger(__name__)


class FileConversionError(Exception):
    """Raised when an uploaded file cannot be converted into an image."""


class UnsupportedFileTypeError(FileConversionError):
    """Raised when a file extension is not supported by the conversion pipeline."""


class CorruptedFileError(FileConversionError):
    """Raised when a supported file cannot be read because it is invalid or corrupted."""


@dataclass(frozen=True)
class PdfPageInfo:
    page_width_pt: float
    page_height_pt: float
    raster_dpi: int


def validate_file_type(file_path: Path) -> None:
    """Validate that the file extension is supported."""
    extension: str = file_path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        allowed: str = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{extension or '<none>'}'. Allowed types: {allowed}."
        )


def load_image(file_path: Path, *, page_number: int = 0, dpi: int = PDF_DPI) -> Image.Image:
    """Load a PDF page as a Pillow image."""
    image, _page_info = load_image_with_page_info(file_path, page_number=page_number, dpi=dpi)
    return image


def load_image_with_page_info(
    file_path: Path,
    *,
    page_number: int = 0,
    dpi: int = PDF_DPI,
) -> tuple[Image.Image, PdfPageInfo]:
    """Load a PDF page and return the raster plus source page geometry."""
    validate_file_type(file_path)

    if not file_path.is_file():
        raise FileConversionError(f"File does not exist: {file_path}")

    return convert_pdf_page_to_image(file_path, page_number=page_number, dpi=dpi)


def rasterize_pdf_bbox(
    file_path: Path,
    bbox: BoundingBox,
    *,
    source_dpi: int,
    target_dpi: int,
    page_number: int = 0,
) -> Image.Image:
    """Rasterize a PDF page region defined in source-dpi pixel coordinates."""
    if source_dpi <= 0 or target_dpi <= 0:
        raise ValueError("source_dpi and target_dpi must be greater than zero.")

    validate_file_type(file_path)
    if not file_path.is_file():
        raise FileConversionError(f"File does not exist: {file_path}")

    x_pt = bbox.x / source_dpi * 72.0
    y_pt = bbox.y / source_dpi * 72.0
    x1_pt = (bbox.x + bbox.width) / source_dpi * 72.0
    y1_pt = (bbox.y + bbox.height) / source_dpi * 72.0
    clip = fitz.Rect(x_pt, y_pt, x1_pt, y1_pt)

    try:
        with fitz.open(file_path) as document:
            if document.page_count == 0:
                raise CorruptedFileError(f"PDF contains no pages: {file_path}")

            if page_number >= document.page_count:
                raise FileConversionError(
                    f"PDF page {page_number} is out of range. "
                    f"Document has {document.page_count} page(s)."
                )

            page = document.load_page(page_number)
            pixmap = page.get_pixmap(dpi=target_dpi, clip=clip, alpha=False)
            image = Image.frombytes(
                mode="RGB",
                size=(pixmap.width, pixmap.height),
                data=pixmap.samples,
            )
            validate_image_dimensions(image)
            return image
    except FileConversionError:
        raise
    except fitz.FileDataError as exc:
        raise CorruptedFileError(f"PDF is invalid or corrupted: {file_path}") from exc
    except fitz.EmptyFileError as exc:
        raise CorruptedFileError(f"PDF is empty: {file_path}") from exc
    except RuntimeError as exc:
        raise CorruptedFileError(f"PDF could not be read: {file_path}") from exc


def convert_pdf_page_to_image(
    file_path: Path,
    *,
    page_number: int = 0,
    dpi: int = PDF_DPI,
) -> tuple[Image.Image, PdfPageInfo]:
    """Convert one PDF page to an RGB Pillow image."""
    if page_number < 0:
        raise ValueError("page_number must be zero or greater.")

    if dpi <= 0:
        raise ValueError("dpi must be greater than zero.")

    try:
        with fitz.open(file_path) as document:
            if document.page_count == 0:
                raise CorruptedFileError(f"PDF contains no pages: {file_path}")

            if page_number >= document.page_count:
                raise FileConversionError(
                    f"PDF page {page_number} is out of range. "
                    f"Document has {document.page_count} page(s)."
                )

            page = document.load_page(page_number)
            rect = page.rect
            raster_dpi = choose_raster_dpi(
                rect.width,
                rect.height,
                preferred_dpi=dpi,
                max_pixels=COMPARE_MAX_RASTER_PIXELS,
            )
            if raster_dpi != dpi:
                logger.info(
                    "Reduced PDF raster DPI from %d to %d for page size %.0fx%.0f pt",
                    dpi,
                    raster_dpi,
                    rect.width,
                    rect.height,
                )

            pixmap = page.get_pixmap(dpi=raster_dpi, alpha=False)

            image = Image.frombytes(
                mode="RGB",
                size=(pixmap.width, pixmap.height),
                data=pixmap.samples,
            )
            validate_image_dimensions(image)
            page_info = PdfPageInfo(
                page_width_pt=float(rect.width),
                page_height_pt=float(rect.height),
                raster_dpi=raster_dpi,
            )
            return image, page_info
    except FileConversionError:
        raise
    except fitz.FileDataError as exc:
        raise CorruptedFileError(f"PDF is invalid or corrupted: {file_path}") from exc
    except fitz.EmptyFileError as exc:
        raise CorruptedFileError(f"PDF is empty: {file_path}") from exc
    except RuntimeError as exc:
        raise CorruptedFileError(f"PDF could not be read: {file_path}") from exc
