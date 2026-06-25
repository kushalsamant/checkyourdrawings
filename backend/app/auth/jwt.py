from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError


def decode_platform_jwt(
    token: str,
    *,
    secret: str,
    issuer: str,
    audience: str,
) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            issuer=issuer,
            audience=audience,
        )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc


def extract_email_from_payload(payload: dict[str, Any]) -> str | None:
    email = payload.get("email")
    if isinstance(email, str) and email:
        return email

    return None
