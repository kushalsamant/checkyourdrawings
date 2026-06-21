#!/usr/bin/env python3
"""Apply SQL migrations in migrations/ in filename order."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "migrations"


def normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def main() -> int:
    database_url = os.environ.get("PLATFORM_DATABASE_URL")
    if not database_url:
        print("PLATFORM_DATABASE_URL is required", file=sys.stderr)
        return 1

    engine = create_engine(normalize_url(database_url), pool_pre_ping=True)
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migration files found")
        return 0

    with engine.begin() as conn:
        for path in files:
            sql = path.read_text(encoding="utf-8")
            print(f"Applying {path.name}...")
            conn.execute(text(sql))

    print(f"Applied {len(files)} migration(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
