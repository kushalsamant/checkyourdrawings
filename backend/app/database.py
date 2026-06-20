from collections.abc import Generator
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.app.config import PLATFORM_DATABASE_URL

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

Base = declarative_base()

_engine: "Engine | None" = None
_SessionLocal: sessionmaker[Session] | None = None


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _get_engine() -> "Engine":
    global _engine, _SessionLocal
    if _engine is None:
        if not PLATFORM_DATABASE_URL:
            raise RuntimeError(
                "PLATFORM_DATABASE_URL is required when CYD_AUTH_REQUIRED=true"
            )
        _engine = create_engine(
            _normalize_database_url(PLATFORM_DATABASE_URL),
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db() -> Generator[Session | None, None, None]:
    if not PLATFORM_DATABASE_URL:
        yield None
        return

    _get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
