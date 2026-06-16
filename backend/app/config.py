from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CYD_",
        env_file=".env",
        extra="ignore",
    )

    max_file_size_mb: int = 100
    pdf_dpi: int = 300
    max_image_pixels: int = 50_000_000
    max_image_dimension: int = 12_000
    output_max_age_hours: int = 24
    compare_timeout_seconds: int = 300
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


_settings = Settings()

BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = BASE_DIR.parent

UPLOAD_DIR: Path = PROJECT_DIR / "uploads"
OUTPUT_DIR: Path = PROJECT_DIR / "outputs"

MAX_FILE_SIZE_MB: int = _settings.max_file_size_mb
PDF_DPI: int = _settings.pdf_dpi
MAX_IMAGE_PIXELS: int = _settings.max_image_pixels
MAX_IMAGE_DIMENSION: int = _settings.max_image_dimension
OUTPUT_MAX_AGE_HOURS: int = _settings.output_max_age_hours
COMPARE_TIMEOUT_SECONDS: int = _settings.compare_timeout_seconds
CORS_ORIGINS: list[str] = _settings.cors_origins
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


def ensure_runtime_directories() -> None:
    """Create directories required for uploaded files and generated outputs."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
