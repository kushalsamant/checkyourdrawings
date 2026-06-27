#!/usr/bin/env python3
"""Production smoke checks for compare API and platform-api account."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
import jwt

from env_file import parse_env_file

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
SECRETS_FILE = REPO_ROOT / ".env.deploy.local"
API_URL = "https://checkyourdrawings-api.onrender.com"
PLATFORM_API_URL = "https://platform-api-1y5i.onrender.com"
SMOKE_EMAIL = "checkyourdrawings-smoke@kvshvl.in"
JOB_POLL_SECONDS = 180
EXPECTED_PROGRESS_STAGES = (
    "queued",
    "loading_drawings",
    "aligning_sheets",
    "preparing_comparison",
    "building_overlay",
    "saving_results",
    "completed",
)


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
        "https://api.render.com/v1/services/srv-d8viasj7uimc738g0h0g/env-vars",
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


def _poll_compare_job(
    client: httpx.Client,
    job_id: str,
    headers: dict[str, str],
) -> dict:
    deadline = time.time() + JOB_POLL_SECONDS
    stages_seen: list[str] = []
    while time.time() < deadline:
        response = client.get(f"{API_URL}/jobs/{job_id}", headers=headers, timeout=60)
        if response.status_code in (502, 503, 504):
            time.sleep(5)
            continue
        response.raise_for_status()
        payload = response.json()
        stage = payload.get("stage")
        if isinstance(stage, str) and (not stages_seen or stages_seen[-1] != stage):
            if stage not in EXPECTED_PROGRESS_STAGES and stage != "failed":
                raise RuntimeError(f"unexpected job stage {stage!r}")
            stages_seen.append(stage)
        status = payload.get("status")
        if status == "completed" and payload.get("result"):
            if stage != "completed":
                raise RuntimeError(f"expected stage=completed, got {stage!r}")
            pipeline_stages = {
                "loading_drawings",
                "aligning_sheets",
                "preparing_comparison",
                "building_overlay",
                "saving_results",
            }
            if not pipeline_stages.intersection(stages_seen):
                raise RuntimeError(f"expected progress stages, saw only {stages_seen}")
            print("job_stages", " -> ".join(stages_seen))
            return payload["result"]
        if status == "failed":
            raise RuntimeError(payload.get("error_message") or "Comparison job failed")
        time.sleep(2)
    raise RuntimeError(f"Comparison job {job_id} did not complete within {JOB_POLL_SECONDS}s")


def _post_compare(
    client: httpx.Client,
    files: dict,
    headers: dict[str, str],
) -> httpx.Response:
    deadline = time.time() + JOB_POLL_SECONDS
    while time.time() < deadline:
        response = client.post(f"{API_URL}/compare", files=files, headers=headers)
        if response.status_code == 409:
            time.sleep(5)
            continue
        return response
    raise RuntimeError("compare queue stayed busy during smoke window")


def _assert_output_paths(image_path: str, pdf_path: str) -> None:
    if image_path.startswith("http://") or image_path.startswith("https://"):
        image_path_only = image_path.split("?", 1)[0]
        pdf_path_only = pdf_path.split("?", 1)[0]
        assert "comparison-" in image_path_only, "expected comparison image URL"
        assert pdf_path_only.endswith(".pdf"), "expected PDF URL"
        return
    assert image_path.startswith("/outputs/comparison-"), "expected output PNG path"
    assert pdf_path.startswith("/outputs/comparison-") and pdf_path.endswith(".pdf"), (
        "expected output PDF path"
    )


def main() -> int:
    secret, issuer = _load_jwt_config()
    access_token = _sign_platform_jwt(email=SMOKE_EMAIL, secret=secret, issuer=issuer)
    auth_headers = {"Authorization": f"Bearer {access_token}"}

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

        account = client.get(f"{PLATFORM_API_URL}/account", headers=auth_headers)
        print("platform_account", account.status_code, account.text[:160])
        if account.status_code != 200:
            return 1

        entitlements = client.get(
            f"{PLATFORM_API_URL}/entitlements",
            params={"app": "checkyourdrawings"},
            headers=auth_headers,
        )
        print("platform_entitlements", entitlements.status_code, entitlements.text[:160])
        if entitlements.status_code != 200:
            return 1

        from backend.tests.fixtures.factory import ContentScenario, image_to_bytes, make_drawing_a_image, make_drawing_b_image
        from backend.tests.fixtures.mvp_assets import resolve_mvp_revision_pairs

        a_img = make_drawing_a_image()
        b_img = make_drawing_b_image(ContentScenario.IDENTICAL, a_img)
        files = {
            "drawing_a": ("a.pdf", image_to_bytes(a_img, ".pdf"), "application/pdf"),
            "drawing_b": ("b.pdf", image_to_bytes(b_img, ".pdf"), "application/pdf"),
        }
        queued = _post_compare(client, files, auth_headers)
        print("authed_compare_synthetic", queued.status_code)
        if queued.status_code != 202:
            print(queued.text[:300])
            return 1

        job_id = queued.json().get("job_id")
        if not job_id:
            print("missing job_id")
            return 1

        payload = _poll_compare_job(client, job_id, auth_headers)
        image_path = payload.get("image_path", "")
        pdf_path = payload.get("pdf_path", "")
        print("image_path", image_path[:100])
        print("pdf_path", pdf_path[:100])
        _assert_output_paths(image_path, pdf_path)

        include_mvp = os.environ.get("SMOKE_INCLUDE_MVP_PDF", "").lower() in ("1", "true", "yes")
        if not include_mvp:
            print(
                "real_pair_level3",
                "SKIP",
                "MVP PDFs OOM on Render free tier; set SMOKE_INCLUDE_MVP_PDF=1 to run",
            )
        mvp_pairs = (
            [pair for pair in resolve_mvp_revision_pairs(REPO_ROOT) if pair[0] == "level3"]
            if include_mvp
            else []
        )
        if include_mvp and not mvp_pairs:
            print("real_pair_level3", "SKIP", "missing PDFs under backend/tests/fixtures/pdfs/")
        for level, drawing_a, drawing_b in mvp_pairs:
            pair_files = {
                "drawing_a": (drawing_a.name, drawing_a.read_bytes(), "application/pdf"),
                "drawing_b": (drawing_b.name, drawing_b.read_bytes(), "application/pdf"),
            }
            response = _post_compare(client, pair_files, auth_headers)
            print(f"real_pair_{level}", response.status_code)
            if response.status_code != 202:
                print(response.text[:300])
                return 1

            result = _poll_compare_job(client, response.json()["job_id"], auth_headers)
            _assert_output_paths(result.get("image_path", ""), result.get("pdf_path", ""))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
