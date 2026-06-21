#!/usr/bin/env python3
"""Apply production environment variables to Render from .env.deploy.local."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

from env_file import parse_env_file

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_KEY_PATH = Path.home() / ".render" / "cli.yaml"
SERVICE_ID = "srv-d8qmgpr7uimc73e5bp9g"
SECRETS_FILE = REPO_ROOT / ".env.deploy.local"

RENDER_KEYS = (
    "AUTH_REQUIRED",
    "CORS_ORIGINS",
    "COMPARE_MAX_RASTER_PIXELS",
    "COMPARE_MAX_WORKERS",
    "PYTHONPATH",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "PLATFORM_DATABASE_URL",
    "PLATFORM_JWT_SECRET",
    "PLATFORM_JWT_ISSUER",
)

# Removed after new keys are set (legacy CYD_* naming).
LEGACY_RENDER_KEYS = (
    "CYD_AUTH_REQUIRED",
    "CYD_CORS_ORIGINS",
    "CYD_COMPARE_MAX_RASTER_PIXELS",
    "CYD_COMPARE_MAX_WORKERS",
)

_LEGACY_KEY_ALIASES: dict[str, str] = {
    "AUTH_REQUIRED": "CYD_AUTH_REQUIRED",
    "CORS_ORIGINS": "CYD_CORS_ORIGINS",
    "COMPARE_MAX_RASTER_PIXELS": "CYD_COMPARE_MAX_RASTER_PIXELS",
    "COMPARE_MAX_WORKERS": "CYD_COMPARE_MAX_WORKERS",
}


def _load_render_key() -> str:
    text = RENDER_KEY_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("key:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("Render API key not found in cli.yaml")


def _env_value(env: dict[str, str], key: str) -> str | None:
    if key in env and env[key]:
        return env[key]
    legacy = _LEGACY_KEY_ALIASES.get(key)
    if legacy and legacy in env and env[legacy]:
        return env[legacy]
    return None


def main() -> int:
    if not SECRETS_FILE.is_file():
        print(f"Missing secrets file: {SECRETS_FILE}", file=sys.stderr)
        return 1

    env = parse_env_file(SECRETS_FILE)
    required = ("AUTH_REQUIRED", "CORS_ORIGINS", "PLATFORM_JWT_SECRET", "PLATFORM_JWT_ISSUER")
    missing = [key for key in required if _env_value(env, key) is None]
    if missing:
        print(
            f"Missing keys in {SECRETS_FILE.name}: {', '.join(missing)} "
            f"(legacy CYD_* names are accepted as fallback)",
            file=sys.stderr,
        )
        return 1

    api_key = _load_render_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    base = f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars"

    with httpx.Client(timeout=60.0) as client:
        for key in RENDER_KEYS:
            value = _env_value(env, key)
            if value is None:
                continue
            response = client.put(
                f"{base}/{key}",
                headers=headers,
                json={"value": value},
            )
            response.raise_for_status()
            print(f"render env set: {key}")

        for legacy_key in LEGACY_RENDER_KEYS:
            response = client.delete(f"{base}/{legacy_key}", headers=headers)
            if response.status_code == 404:
                print(f"render env already absent: {legacy_key}")
                continue
            response.raise_for_status()
            print(f"render env deleted: {legacy_key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
