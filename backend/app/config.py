from pathlib import Path


BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = BASE_DIR.parent

UPLOAD_DIR: Path = PROJECT_DIR / "uploads"
OUTPUT_DIR: Path = PROJECT_DIR / "outputs"

MAX_FILE_SIZE_MB: int = 100
PDF_DPI: int = 300
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


def ensure_runtime_directories() -> None:
    """Create directories required for uploaded files and generated outputs."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


ensure_runtime_directories()
