from pathlib import Path

import fitz
from PIL import Image

from backend.app.config import ALLOWED_EXTENSIONS, PDF_DPI
from backend.app.services.image_limits import validate_image_dimensions


class FileConversionError(Exception):
    """Raised when an uploaded file cannot be converted into an image."""


class UnsupportedFileTypeError(FileConversionError):
    """Raised when a file extension is not supported by the conversion pipeline."""


class CorruptedFileError(FileConversionError):
    """Raised when a supported file cannot be read because it is invalid or corrupted."""


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
    validate_file_type(file_path)

    if not file_path.is_file():
        raise FileConversionError(f"File does not exist: {file_path}")

    return convert_pdf_page_to_image(file_path, page_number=page_number, dpi=dpi)


def convert_pdf_page_to_image(
    file_path: Path,
    *,
    page_number: int = 0,
    dpi: int = PDF_DPI,
) -> Image.Image:
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
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)

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
