import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import ezdxf  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from ezdxf.addons.drawing import Frontend, RenderContext  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402
from PIL import Image

from backend.app.config import ODA_CONVERTER_PATH, PDF_DPI
from backend.app.services.image_limits import validate_image_dimensions
from backend.app.services.pdf_converter import FileConversionError


logger = logging.getLogger(__name__)

ODA_OUTPUT_VERSION: str = "ACAD2007"
ODA_OUTPUT_FORMAT: str = "DXF"


class DwgConversionError(FileConversionError):
    """Raised when a DWG file cannot be converted for comparison."""


def convert_dwg_to_image(file_path: Path, *, dpi: int = PDF_DPI) -> Image.Image:
    """Convert a DWG file to a Pillow RGB image via ODA File Converter and ezdxf."""
    if dpi <= 0:
        raise ValueError("dpi must be greater than zero.")

    dxf_path, temp_root = convert_dwg_to_dxf(file_path)
    try:
        return rasterize_dxf_to_image(dxf_path, dpi=dpi)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def convert_dwg_to_dxf(file_path: Path) -> tuple[Path, Path]:
    """Run ODA File Converter to produce a DXF in a temp output folder."""
    converter = _resolve_oda_converter_path()
    if converter is None:
        raise DwgConversionError(
            "DWG conversion is not configured. Set CYD_ODA_CONVERTER_PATH to the "
            "ODA File Converter executable, or run inside the production Docker image."
        )

    if not file_path.is_file():
        raise DwgConversionError(f"DWG file does not exist: {file_path}")

    temp_root = Path(tempfile.mkdtemp(prefix="cyd_dwg_"))
    input_dir = temp_root / "in"
    output_dir = temp_root / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    staged_input = input_dir / file_path.name
    shutil.copy2(file_path, staged_input)

    command = [
        str(converter),
        str(input_dir),
        str(output_dir),
        ODA_OUTPUT_VERSION,
        ODA_OUTPUT_FORMAT,
        "0",
        "1",
        file_path.name,
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise DwgConversionError(f"ODA File Converter timed out for {file_path.name}.") from exc
    except OSError as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise DwgConversionError(f"Could not run ODA File Converter: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        shutil.rmtree(temp_root, ignore_errors=True)
        raise DwgConversionError(
            f"ODA File Converter failed for {file_path.name}"
            + (f": {detail}" if detail else ".")
        )

    dxf_candidates = sorted(output_dir.rglob("*.dxf"))
    if not dxf_candidates:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise DwgConversionError(f"ODA File Converter produced no DXF for {file_path.name}.")

    return dxf_candidates[0], temp_root


def rasterize_dxf_to_image(dxf_path: Path, *, dpi: int) -> Image.Image:
    """Rasterize model space from a DXF file to an RGB Pillow image."""
    try:
        document = ezdxf.readfile(dxf_path)
    except ezdxf.DXFError as exc:
        raise DwgConversionError(f"DXF is invalid or corrupted: {dxf_path}") from exc

    figure = plt.figure(dpi=dpi)
    axes = figure.add_axes([0.0, 0.0, 1.0, 1.0])
    axes.set_axis_off()

    try:
        context = RenderContext(document)
        backend = MatplotlibBackend(axes)
        Frontend(context, backend).draw_layout(document.modelspace(), finalize=True)

        figure.canvas.draw()
        width, height = figure.canvas.get_width_height()
        buffer = figure.canvas.buffer_rgba()
        image_array = Image.frombuffer("RGBA", (width, height), buffer).convert("RGB")
        validate_image_dimensions(image_array)
        return image_array
    except Exception as exc:
        raise DwgConversionError(f"Could not rasterize DXF: {dxf_path}") from exc
    finally:
        plt.close(figure)


def _resolve_oda_converter_path() -> Path | None:
    if ODA_CONVERTER_PATH:
        configured = Path(ODA_CONVERTER_PATH)
        if configured.is_file():
            return configured

    for candidate_name in ("ODAFileConverter.exe", "ODAFileConverter"):
        discovered = shutil.which(candidate_name)
        if discovered:
            return Path(discovered)

    return None
