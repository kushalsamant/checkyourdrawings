#!/usr/bin/env python3
"""Apply Pass 3 environment variables to Render from .env.pass3.local."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDER_KEY_PATH = Path.home() / ".render" / "cli.yaml"
SERVICE_ID = "srv-d8qmgpr7uimc73e5bp9g"
SECRETS_FILE = REPO_ROOT / ".env.pass3.local"

RENDER_KEYS = (
    "CYD_AUTH_REQUIRED",
    "CYD_CORS_ORIGINS",
    "PYTHONPATH",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "PLATFORM_DATABASE_URL",
)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _load_render_key() -> str:
    text = RENDER_KEY_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("key:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("Render API key not found in cli.yaml")


def main() -> int:
    if not SECRETS_FILE.is_file():
        print(f"Missing secrets file: {SECRETS_FILE}", file=sys.stderr)
        return 1

    env = _parse_env_file(SECRETS_FILE)
    missing = [key for key in RENDER_KEYS if key not in env]
    if missing:
        print(f"Missing keys in {SECRETS_FILE.name}: {', '.join(missing)}", file=sys.stderr)
        return 1

    api_key = _load_render_key()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60.0) as client:
        for key in RENDER_KEYS:
            response = client.put(
                f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars/{key}",
                headers=headers,
                json={"value": env[key]},
            )
            response.raise_for_status()
            print(f"render env set: {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
