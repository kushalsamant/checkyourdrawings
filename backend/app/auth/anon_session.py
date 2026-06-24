import re
import uuid

from fastapi import Header, HTTPException, status

_ANON_SESSION_HEADER = "X-Anon-Session"
_UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_valid_anon_session_id(value: str | None) -> bool:
    if not value:
        return False
    return _UUID_V4_PATTERN.match(value.strip()) is not None


def normalize_anon_session_id(value: str) -> str:
    return value.strip().lower()


def get_anon_session_id(
    x_anon_session: str | None = Header(None, alias=_ANON_SESSION_HEADER),
) -> str | None:
    if x_anon_session is None:
        return None
    if not is_valid_anon_session_id(x_anon_session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid anonymous session identifier.",
        )
    return normalize_anon_session_id(x_anon_session)


def require_anon_session_id(
    x_anon_session: str | None = Header(None, alias=_ANON_SESSION_HEADER),
) -> str:
    session_id = get_anon_session_id(x_anon_session=x_anon_session)
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anonymous session identifier is required.",
        )
    return session_id


def new_anon_session_id() -> str:
    return str(uuid.uuid4()).lower()
