import logging

import httpx

from backend.app.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

CYD_OUTPUTS_BUCKET = "cyd_outputs"


def upload_png_bytes(png_bytes: bytes, remote_path: str) -> str:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for cloud storage."
        )

    base_url = SUPABASE_URL.rstrip("/")
    normalized_path = remote_path.lstrip("/")
    upload_url = f"{base_url}/storage/v1/object/{CYD_OUTPUTS_BUCKET}/{normalized_path}"

    response = httpx.post(
        upload_url,
        content=png_bytes,
        headers={
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "image/png",
            "x-upsert": "true",
        },
        timeout=60.0,
    )
    if response.status_code >= 400:
        logger.error(
            "Supabase upload failed (%s): %s",
            response.status_code,
            response.text,
        )
        response.raise_for_status()

    return f"{base_url}/storage/v1/object/public/{CYD_OUTPUTS_BUCKET}/{normalized_path}"
