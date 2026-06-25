from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.auth.jwt import decode_platform_jwt, extract_email_from_payload
from backend.app.auth.user import AuthenticatedUser
from backend.app.config import AUTH_REQUIRED, PLATFORM_JWT_ISSUER, PLATFORM_JWT_SECRET
from backend.app.services.platform_client import _DEFAULT_ENTITLEMENT, fetch_entitlements

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser | None:
    if credentials is None:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue.",
            )
        return None

    if not PLATFORM_JWT_SECRET:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication token verification is not configured.",
            )
        return None

    payload = decode_platform_jwt(
        credentials.credentials,
        secret=PLATFORM_JWT_SECRET,
        issuer=PLATFORM_JWT_ISSUER or "https://auth.kvshvl.in",
        audience="kvshvl-platform",
    )
    email = extract_email_from_payload(payload)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    try:
        entitlements = fetch_entitlements(credentials.credentials)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED or AUTH_REQUIRED:
            raise
        entitlements = dict(_DEFAULT_ENTITLEMENT)
    tier = entitlements.get("tier")
    paid = bool(entitlements.get("paid"))
    priority = bool(entitlements.get("priority"))
    enabled = entitlements.get("enabled", True)
    if enabled is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this app is disabled for your account.",
        )

    return AuthenticatedUser(
        email=email,
        name=payload.get("name") if isinstance(payload.get("name"), str) else None,
        google_id=payload.get("sub") if isinstance(payload.get("sub"), str) else None,
        paid=paid,
        priority=priority,
        tier=tier if isinstance(tier, str) else "free",
    )
