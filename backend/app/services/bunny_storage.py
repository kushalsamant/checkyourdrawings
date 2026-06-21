import base64
import hashlib
import logging
import time
from pathlib import Path

import httpx

from backend.app.config import (
    BUNNY_CDN_HOSTNAME,
    BUNNY_SIGNED_URL_TTL_SECONDS,
    BUNNY_STORAGE_ACCESS_KEY,
    BUNNY_STORAGE_PREFIX,
    BUNNY_STORAGE_REGION,
    BUNNY_STORAGE_ZONE,
    BUNNY_TOKEN_AUTH_KEY,
)

logger = logging.getLogger(__name__)

APP_PREFIX = "checkyourdrawings"


def bunny_enabled() -> bool:
    return bool(
        BUNNY_STORAGE_ZONE
        and BUNNY_STORAGE_ACCESS_KEY
        and BUNNY_CDN_HOSTNAME
        and BUNNY_TOKEN_AUTH_KEY
    )


def _storage_base_url() -> str:
    region = (BUNNY_STORAGE_REGION or "ny").strip().lower()
    zone = BUNNY_STORAGE_ZONE
    assert zone is not None
    return f"https://{region}.storage.bunnycdn.com/{zone}"


def remote_path(relative_path: str) -> str:
    cleaned = relative_path.replace("\\", "/").lstrip("/")
    prefix = BUNNY_STORAGE_PREFIX.rstrip("/")
    return f"{prefix}/{cleaned}" if prefix else cleaned


def upload_file(local_path: Path, relative_path: str) -> str:
    if not bunny_enabled():
        raise RuntimeError("Bunny storage is not configured.")

    target = remote_path(relative_path)
    url = f"{_storage_base_url()}/{target}"
    data = local_path.read_bytes()
    response = httpx.put(
        url,
        content=data,
        headers={
            "AccessKey": BUNNY_STORAGE_ACCESS_KEY or "",
            "Content-Type": "application/octet-stream",
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return signed_cdn_url(target)


def signed_cdn_url(path: str, ttl_seconds: int | None = None) -> str:
    if not bunny_enabled():
        raise RuntimeError("Bunny CDN is not configured.")

    expires = int(time.time()) + (ttl_seconds or BUNNY_SIGNED_URL_TTL_SECONDS)
    normalized = path.replace("\\", "/").lstrip("/")
    token_path = f"/{normalized}"
    hashable = f"{BUNNY_TOKEN_AUTH_KEY}{token_path}{expires}"
    digest = hashlib.sha256(hashable.encode("utf-8")).digest()
    token = (
        base64.b64encode(digest)
        .decode("utf-8")
        .replace("\n", "")
        .replace("+", "-")
        .replace("/", "_")
        .replace("=", "")
    )
    hostname = BUNNY_CDN_HOSTNAME
    assert hostname is not None
    return f"https://{hostname}{token_path}?token={token}&expires={expires}"


def delete_file(relative_path: str) -> None:
    if not bunny_enabled():
        return

    target = remote_path(relative_path)
    url = f"{_storage_base_url()}/{target}"
    try:
        response = httpx.delete(
            url,
            headers={"AccessKey": BUNNY_STORAGE_ACCESS_KEY or ""},
            timeout=60.0,
        )
        if response.status_code not in (200, 404):
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to delete Bunny object %s: %s", target, exc)


def publish_comparison_outputs(output_id: str, image_path: Path, pdf_path: Path) -> tuple[str, str]:
    image_key = f"comparison-{output_id}.png"
    pdf_key = f"comparison-{output_id}.pdf"
    image_url = upload_file(image_path, image_key)
    pdf_url = upload_file(pdf_path, pdf_key)
    return image_url, pdf_url
