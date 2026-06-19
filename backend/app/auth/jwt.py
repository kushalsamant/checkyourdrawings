from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError


@lru_cache(maxsize=4)
def _jwks_client(supabase_url: str) -> PyJWKClient:
    return PyJWKClient(f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def decode_supabase_jwt(
    token: str,
    *,
    secret: str | None = None,
    supabase_url: str | None = None,
) -> dict[str, Any]:
    try:
        if secret:
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        if supabase_url:
            signing_key = _jwks_client(supabase_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience="authenticated",
            )
        raise ValueError("JWT verification requires secret or supabase_url")
    except (PyJWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc


def extract_email_from_payload(payload: dict[str, Any]) -> str | None:
    email = payload.get("email")
    if isinstance(email, str) and email:
        return email

    user_metadata = payload.get("user_metadata")
    if isinstance(user_metadata, dict):
        metadata_email = user_metadata.get("email")
        if isinstance(metadata_email, str) and metadata_email:
            return metadata_email

    return None
