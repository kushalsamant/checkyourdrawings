from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,"
    "http://localhost:5173,"
    "http://127.0.0.1:3000,"
    "http://127.0.0.1:5173"
)


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        extra="ignore",
    )

    platform_database_url: str | None = None
    platform_jwt_secret: str | None = None
    platform_jwt_issuer: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None


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
    compare_max_raster_pixels: int = 4_000_000
    compare_max_workers: int = 1
    compare_disable_ecc_above_pixels: int = 3_000_000
    alignment_large_image_pixels: int = 3_000_000
    alignment_large_image_max_features: int = 5_000
    content_bbox_padding_ratio: float = 0.02
    min_overlap_area_ratio: float = 0.05
    alignment_marginal_inlier_ratio: float = 0.55
    alignment_ecc_refinement: bool = True
    auth_required: bool = False
    cors_origins: str = Field(default=_DEFAULT_CORS_ORIGINS)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


_settings = Settings()
_platform_settings = PlatformSettings()

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
COMPARE_MAX_RASTER_PIXELS: int = _settings.compare_max_raster_pixels
COMPARE_MAX_WORKERS: int = _settings.compare_max_workers
COMPARE_DISABLE_ECC_ABOVE_PIXELS: int = _settings.compare_disable_ecc_above_pixels
ALIGNMENT_LARGE_IMAGE_PIXELS: int = _settings.alignment_large_image_pixels
ALIGNMENT_LARGE_IMAGE_MAX_FEATURES: int = _settings.alignment_large_image_max_features
CONTENT_BBOX_PADDING_RATIO: float = _settings.content_bbox_padding_ratio
MIN_OVERLAP_AREA_RATIO: float = _settings.min_overlap_area_ratio
ALIGNMENT_MARGINAL_INLIER_RATIO: float = _settings.alignment_marginal_inlier_ratio
ALIGNMENT_ECC_REFINEMENT: bool = _settings.alignment_ecc_refinement
AUTH_REQUIRED: bool = _settings.auth_required
CORS_ORIGINS: list[str] = _settings.cors_origins_list
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf"})

PLATFORM_DATABASE_URL: str | None = _platform_settings.platform_database_url
PLATFORM_JWT_SECRET: str | None = _platform_settings.platform_jwt_secret
PLATFORM_JWT_ISSUER: str | None = _platform_settings.platform_jwt_issuer
SUPABASE_URL: str | None = _platform_settings.supabase_url
SUPABASE_SERVICE_ROLE_KEY: str | None = _platform_settings.supabase_service_role_key
SUPABASE_JWT_SECRET: str | None = _platform_settings.supabase_jwt_secret


def get_settings() -> Settings:
    return _settings


def get_platform_settings() -> PlatformSettings:
    return _platform_settings


def ensure_runtime_directories() -> None:
    """Create directories required for uploaded files and generated outputs."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
