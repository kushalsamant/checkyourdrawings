#!/usr/bin/env python3
"""Pass 3 production smoke checks using Supabase admin + compare API."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_FILE = REPO_ROOT / ".env.pass3.local"
API_URL = "https://checkyourdrawings.onrender.com"
TEST_EMAIL = "cyd-smoke@kvshvl.in"
TEST_PASSWORD = "CYD-Smoke-Test-2026!"


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    if not SECRETS_FILE.is_file():
        print(f"Missing {SECRETS_FILE}", file=sys.stderr)
        return 1

    env = _parse_env_file(SECRETS_FILE)
    supabase_url = env["SUPABASE_URL"].rstrip("/")
    service_role = env["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {
        "Authorization": f"Bearer {service_role}",
        "apikey": service_role,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120.0) as client:
        ready = client.get(f"{API_URL}/health/ready")
        print("health/ready", ready.status_code, ready.text)

        unsigned = client.post(f"{API_URL}/compare", files={})
        print("unsigned_compare", unsigned.status_code, unsigned.text[:120])

        client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=headers,
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "email_confirm": True},
        )

        token_response = client.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": env["VITE_SUPABASE_ANON_KEY"], "Content-Type": "application/json"},
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        print("auth_token_ok", bool(access_token))

        from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image

        a_img = make_drawing_a_image()
        b_img = make_drawing_b_image(ContentScenario.IDENTICAL, a_img)
        files = {
            "drawing_a": ("a.pdf", image_to_bytes(a_img, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(b_img, ".pdf"), "application/pdf"),
        }
        authed = client.post(
            f"{API_URL}/compare",
            files=files,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        print("authed_compare", authed.status_code)
        if authed.status_code == 200:
            image_path = authed.json().get("image_path", "")
            print("image_path", image_path[:100])
            assert "supabase.co/storage" in image_path, "expected Supabase storage URL"
        else:
            print(authed.text[:300])
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
