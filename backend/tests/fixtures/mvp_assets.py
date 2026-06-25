"""Committed MVP revision PDF fixtures for end-to-end compare tests."""

from __future__ import annotations

from pathlib import Path

import pytest

MVP_PDF_DIR = Path(__file__).resolve().parent / "pdfs"

ASSET_SOURCE_MAP: dict[str, tuple[str, str]] = {
    "level0": ("0A 02-Saurabh mishraR2-Model.pdf", "0B 02-Saurabh mishraR2-Model.pdf"),
    "level1": ("1A 02-Saurabh mishraR2-Model.pdf", "1B 02-Saurabh mishraR2-Model.pdf"),
    "level2": ("2A 02-Saurabh mishraR2-Model.pdf", "2B 02-Saurabh mishraR2-Model.pdf"),
    "level3": ("3A 02-Saurabh mishraR2-Model.pdf", "3B 02-Saurabh mishraR2-Model.pdf"),
}


def _fixture_path(level: str, side: str) -> Path:
    return MVP_PDF_DIR / f"{level}_{side}.pdf"


def mvp_assets_available() -> bool:
    """Return True when all committed MVP fixture PDFs are present."""
    for level in ASSET_SOURCE_MAP:
        if not _fixture_path(level, "a").is_file() or not _fixture_path(level, "b").is_file():
            return False
    return True


def resolve_mvp_revision_pairs(repo_root: Path | None = None) -> list[tuple[str, Path, Path]]:
    """Return revision pairs, preferring committed fixtures with assets/ fallback."""
    if mvp_assets_available():
        return [
            (level, _fixture_path(level, "a"), _fixture_path(level, "b"))
            for level in ASSET_SOURCE_MAP
        ]

    root = repo_root or Path(__file__).resolve().parents[3]
    assets_dir = root / "assets"
    if not assets_dir.is_dir():
        return []

    pairs: list[tuple[str, Path, Path]] = []
    for level, (drawing_a_name, drawing_b_name) in ASSET_SOURCE_MAP.items():
        drawing_a = assets_dir / drawing_a_name
        drawing_b = assets_dir / drawing_b_name
        if drawing_a.is_file() and drawing_b.is_file():
            pairs.append((level, drawing_a, drawing_b))
    return pairs


MVP_REVISION_PAIRS: list[tuple[str, Path, Path]] = [
    (level, _fixture_path(level, "a"), _fixture_path(level, "b"))
    for level in ASSET_SOURCE_MAP
]


def require_mvp_assets() -> None:
    """Skip the current test when MVP fixture PDFs are unavailable."""
    if not mvp_assets_available():
        pytest.skip("MVP PDF fixtures are not available under backend/tests/fixtures/pdfs/")
