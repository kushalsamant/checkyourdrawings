#!/usr/bin/env python3
"""Production smoke checks for compare API and platform-api account."""

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
PLATFORM_API_URL = "https://platform-api-1y5i.onrender.com"
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


def _load_jwt_config() -> tuple[str, str]:
    if SECRETS_FILE.is_file():
        env = parse_env_file(SECRETS_FILE)
        secret = env.get("PLATFORM_JWT_SECRET") or env.get("CYD_PLATFORM_JWT_SECRET")
        issuer = env.get("PLATFORM_JWT_ISSUER") or env.get("CYD_PLATFORM_JWT_ISSUER")
        if secret and issuer:
            return secret, issuer

    from pathlib import Path as _Path

    text = _Path.home().joinpath(".render/cli.yaml").read_text(encoding="utf-8")
    render_key = next(
        line.split(":", 1)[1].strip()
        for line in text.splitlines()
        if line.strip().startswith("key:")
    )
    headers = {"Authorization": f"Bearer {render_key}"}
    response = httpx.get(
        "https://api.render.com/v1/services/srv-d8qmgpr7uimc73e5bp9g/env-vars",
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    secret = None
    issuer = None
    for item in response.json():
        env_var = item.get("envVar") or item
        if env_var.get("key") == "PLATFORM_JWT_SECRET":
            secret = env_var.get("value")
        if env_var.get("key") == "PLATFORM_JWT_ISSUER":
            issuer = env_var.get("value")
    if not secret or not issuer:
        raise RuntimeError("Could not load PLATFORM_JWT_SECRET / PLATFORM_JWT_ISSUER")
    return secret, issuer


def main() -> int:
    secret, issuer = _load_jwt_config()
    access_token = _sign_platform_jwt(email=SMOKE_EMAIL, secret=secret, issuer=issuer)

    with httpx.Client(timeout=180.0) as client:
        ready = client.get(f"{API_URL}/health/ready")
        print("health/ready", ready.status_code, ready.text)
        if ready.status_code != 200:
            return 1
        ready_payload = ready.json()
        if ready_payload.get("status") != "ok":
            print("health/ready degraded:", ready_payload)
            return 1

        unsigned = client.post(f"{API_URL}/compare", files={})
        print("unsigned_compare", unsigned.status_code, unsigned.text[:120])

        account = client.get(
            f"{PLATFORM_API_URL}/account",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        print("platform_account", account.status_code, account.text[:160])
        if account.status_code != 200:
            return 1

        entitlements = client.get(
            f"{PLATFORM_API_URL}/entitlements",
            params={"app": "checkyourdrawings"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        print("platform_entitlements", entitlements.status_code, entitlements.text[:160])
        if entitlements.status_code != 200:
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
