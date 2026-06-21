"""In-memory per-IP sliding-window rate limiter.

State is per-process. The API runs as a single Render web service with one
worker, so a process-local limiter is sufficient to throttle abusive clients
without an external store. Limits are read from module-level names so tests can
monkeypatch them.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from backend.app.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_MAX_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)

ENABLED: bool = RATE_LIMIT_ENABLED
MAX_REQUESTS: int = RATE_LIMIT_MAX_REQUESTS
WINDOW_SECONDS: int = RATE_LIMIT_WINDOW_SECONDS

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def reset() -> None:
    """Clear all recorded hits. Intended for test isolation."""
    with _lock:
        _hits.clear()


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit_compare(request: Request) -> None:
    if not ENABLED:
        return

    key = _client_key(request)
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS

    with _lock:
        hits = _hits[key]
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= MAX_REQUESTS:
            retry_after = max(1, int(hits[0] + WINDOW_SECONDS - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
