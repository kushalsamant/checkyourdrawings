import logging

import httpx
from fastapi import HTTPException, status

from backend.app.config import PLATFORM_API_URL

logger = logging.getLogger(__name__)

APP_ID = "checkyourdrawings"
_DEFAULT_ENTITLEMENT = {
    "app_id": APP_ID,
    "enabled": True,
    "paid": False,
    "priority": False,
    "tier": "trial",
}


def fetch_entitlements(access_token: str) -> dict[str, object]:
    if not PLATFORM_API_URL:
        return dict(_DEFAULT_ENTITLEMENT)

    url = f"{PLATFORM_API_URL.rstrip('/')}/entitlements"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                params={"app": APP_ID},
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        logger.warning("Platform entitlements request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform account service is unavailable.",
        ) from exc

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform account service is unavailable.",
        )

    if not response.is_success:
        logger.warning(
            "Platform entitlements returned HTTP %s: %s",
            response.status_code,
            response.text[:200],
        )
        return dict(_DEFAULT_ENTITLEMENT)

    payload = response.json()
    if not isinstance(payload, dict):
        return dict(_DEFAULT_ENTITLEMENT)
    return payload
