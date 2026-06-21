#!/usr/bin/env python3
"""Production smoke checks for compare API and platform JWT auth."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import jwt

from env_file import parse_env_file

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
SECRETS_FILE = REPO_ROOT / ".env.deploy.local"
API_URL = "https://checkyourdrawings.onrender.com"
SMOKE_EMAIL = "checkyourdrawings-smoke@kvshvl.in"


def _sign_platform_jwt(*, email: str, secret: str, issuer: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "email": email,
            "sub": "checkyourdrawings-smoke-test",
            "name": "Check Your Drawings Smoke Test",
            "iss": issuer,
            "aud": "kvshvl-platform",
            "iat": now,
            "exp": now + 3600,
        },
        secret,
        algorithm="HS256",
    )


def main() -> int:
    if not SECRETS_FILE.is_file():
        print(f"Missing {SECRETS_FILE}", file=sys.stderr)
        return 1

    env = parse_env_file(SECRETS_FILE)
    for key in ("PLATFORM_JWT_SECRET", "PLATFORM_JWT_ISSUER"):
        if key not in env or not env[key]:
            print(f"Missing {key} in {SECRETS_FILE.name}", file=sys.stderr)
            return 1

    access_token = _sign_platform_jwt(
        email=SMOKE_EMAIL,
        secret=env["PLATFORM_JWT_SECRET"],
        issuer=env["PLATFORM_JWT_ISSUER"],
    )

    with httpx.Client(timeout=180.0) as client:
        ready = client.get(f"{API_URL}/health/ready")
        print("health/ready", ready.status_code, ready.text)

        unsigned = client.post(f"{API_URL}/compare", files={})
        print("unsigned_compare", unsigned.status_code, unsigned.text[:120])

        account = client.get(
            f"{API_URL}/account",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        print("authed_account", account.status_code, account.text[:160])
        if account.status_code != 200:
            return 1

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
        print("authed_compare_synthetic", authed.status_code)
        if authed.status_code == 200:
            payload = authed.json()
            image_path = payload.get("image_path", "")
            pdf_path = payload.get("pdf_path", "")
            print("image_path", image_path[:100])
            print("pdf_path", pdf_path[:100])
            assert image_path.startswith("/outputs/comparison-"), "expected Render output PNG path"
            assert pdf_path.startswith("/outputs/comparison-") and pdf_path.endswith(".pdf"), (
                "expected Render output PDF path"
            )
        else:
            print(authed.text[:300])
            return 1

        pair_prefixes = ("0A", "1A", "2A", "3A")
        for prefix in pair_prefixes:
            drawing_a = next(REPO_ROOT.glob(f"{prefix}*.pdf"), None)
            drawing_b = next(REPO_ROOT.glob(f"{prefix[0]}B*.pdf"), None)
            if drawing_a is None or drawing_b is None:
                print(f"real_pair_{prefix[0]}A/{prefix[0]}B", "SKIP", "missing PDFs")
                continue

            pair_files = {
                "drawing_a": (
                    drawing_a.name,
                    drawing_a.read_bytes(),
                    "application/pdf",
                ),
                "drawing_b": (
                    drawing_b.name,
                    drawing_b.read_bytes(),
                    "application/pdf",
                ),
            }
            response = client.post(
                f"{API_URL}/compare",
                files=pair_files,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            label = f"{prefix[0]}A/{prefix[0]}B"
            print(f"real_pair_{label}", response.status_code)
            if response.status_code != 200:
                print(response.text[:300])
                return 1

            image_path = response.json().get("image_path", "")
            pdf_path = response.json().get("pdf_path", "")
            assert image_path.startswith("/outputs/comparison-"), f"{label} expected Render PNG path"
            assert pdf_path.startswith("/outputs/comparison-") and pdf_path.endswith(".pdf"), (
                f"{label} expected Render PDF path"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
