#!/usr/bin/env python3
"""Apply production environment variables to Render from .env.deploy.local."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

from env_file import parse_env_file

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_KEY_PATH = Path.home() / ".render" / "cli.yaml"
SERVICE_ID = "srv-d8viasj7uimc738g0h0g"
SECRETS_FILE = REPO_ROOT / ".env.deploy.local"
PLATFORM_SECRETS_FILE = REPO_ROOT.parent / "platform-api" / ".env.deploy.local"
BUNNY_SECRETS_FILE = REPO_ROOT / ".env.bunnynet"

DEFAULT_RENDER_ENV: dict[str, str] = {
    "AUTH_REQUIRED": "true",
    "ANONYMOUS_ALLOWANCE_TOTAL": "5",
    "MAX_ANON_ACTIVE_JOBS": "1",
    "MAX_FREE_ACTIVE_JOBS": "1",
    "MAX_PRO_ACTIVE_JOBS": "10",
    "CORS_ORIGINS": (
        "https://checkyourdrawings.kvshvl.in,"
        "https://www.checkyourdrawings.kvshvl.in,"
        "http://localhost:5173"
    ),
    "COMPARE_MAX_RASTER_PIXELS": "4000000",
    "COMPARE_MAX_WORKERS": "1",
    "PYTHONPATH": "/app",
    "PLATFORM_API_URL": "https://platform-api.kvshvl.in",
    "BUNNY_STORAGE_REGION": "ny",
    "BUNNY_STORAGE_PREFIX": "checkyourdrawings",
    "BUNNY_CDN_HOSTNAME": "kvshvl-platform-cdn.b-cdn.net",
    "BUNNY_SIGNED_URL_TTL_SECONDS": "86400",
}

RENDER_KEYS = (
    "AUTH_REQUIRED",
    "ANONYMOUS_ALLOWANCE_TOTAL",
    "MAX_ANON_ACTIVE_JOBS",
    "MAX_FREE_ACTIVE_JOBS",
    "MAX_PRO_ACTIVE_JOBS",
    "CORS_ORIGINS",
    "COMPARE_MAX_RASTER_PIXELS",
    "COMPARE_MAX_WORKERS",
    "PYTHONPATH",
    "PLATFORM_API_URL",
    "PLATFORM_DATABASE_URL",
    "PLATFORM_JWT_SECRET",
    "PLATFORM_JWT_ISSUER",
    "BUNNY_STORAGE_ZONE",
    "BUNNY_STORAGE_ACCESS_KEY",
    "BUNNY_STORAGE_REGION",
    "BUNNY_STORAGE_PREFIX",
    "BUNNY_CDN_HOSTNAME",
    "BUNNY_TOKEN_AUTH_KEY",
    "BUNNY_SIGNED_URL_TTL_SECONDS",
)

DELETE_RENDER_KEYS = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "CYD_AUTH_REQUIRED",
    "CYD_CORS_ORIGINS",
    "CYD_COMPARE_MAX_RASTER_PIXELS",
    "CYD_COMPARE_MAX_WORKERS",
)


def _load_render_key() -> str:
    text = RENDER_KEY_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("key:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("Render API key not found in cli.yaml")


def _build_render_env() -> dict[str, str]:
    merged = dict(DEFAULT_RENDER_ENV)
    for path in (PLATFORM_SECRETS_FILE, BUNNY_SECRETS_FILE, SECRETS_FILE):
        if path.is_file():
            merged.update(parse_env_file(path))

    legacy_auth = merged.pop("CYD_AUTH_REQUIRED", None)
    legacy_cors = merged.pop("CYD_CORS_ORIGINS", None)
    if legacy_auth is not None and not merged.get("AUTH_REQUIRED"):
        merged["AUTH_REQUIRED"] = legacy_auth
    if legacy_cors and not merged.get("CORS_ORIGINS"):
        merged["CORS_ORIGINS"] = legacy_cors

    if not merged.get("BUNNY_STORAGE_ZONE"):
        merged["BUNNY_STORAGE_ZONE"] = merged.get("STORAGE_ZONE_NAME", "")
    if not merged.get("BUNNY_STORAGE_ACCESS_KEY"):
        merged["BUNNY_STORAGE_ACCESS_KEY"] = merged.get("STORAGE_ZONE_PASSWORD", "")

    if not merged.get("BUNNY_TOKEN_AUTH_KEY"):
        bunny_key_csv = REPO_ROOT.parent / "bunny-live-key.csv"
        if bunny_key_csv.is_file():
            for line in bunny_key_csv.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("pull_zone_name,"):
                    continue
                parts = line.split(",")
                if len(parts) >= 4 and parts[3].strip():
                    merged["BUNNY_TOKEN_AUTH_KEY"] = parts[3].strip()
                    break

    for drop_key in (
        "STORAGE_ZONE_NAME",
        "STORAGE_ZONE_PASSWORD",
        "STORAGE_ZONE_HOSTNAME",
        "STORAGE_ZONE_ID",
        "STORAGE_ZONE_LINKED_HOSTNAME",
        "STORAGE_ZONE_READ_ONLY_PASSWORD",
        "STORAGE_ZONE_CONNECTION_TYPE",
        "STORAGE_ZONE_PORT",
        "BUNNY_ACCOUNT_API_KEY",
    ):
        merged.pop(drop_key, None)

    return merged


def main() -> int:
    env = _build_render_env()
    required = ("AUTH_REQUIRED", "CORS_ORIGINS", "PLATFORM_JWT_SECRET", "PLATFORM_JWT_ISSUER", "PLATFORM_DATABASE_URL")
    missing = [key for key in required if not env.get(key)]
    if missing:
        print(f"Missing keys after merging deploy secrets: {', '.join(missing)}", file=sys.stderr)
        return 1

    api_key = _load_render_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    base = f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars"

    with httpx.Client(timeout=60.0) as client:
        for key in RENDER_KEYS:
            value = env.get(key, "")
            if not value:
                continue
            response = client.put(
                f"{base}/{key}",
                headers=headers,
                json={"value": value},
            )
            response.raise_for_status()
            print(f"render env set: {key}")

        for delete_key in DELETE_RENDER_KEYS:
            response = client.delete(f"{base}/{delete_key}", headers=headers)
            if response.status_code == 404:
                print(f"render env already absent: {delete_key}")
                continue
            response.raise_for_status()
            print(f"render env deleted: {delete_key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
