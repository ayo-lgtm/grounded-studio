"""Create or upgrade the database. Safe to run on every start.

Usage (any platform, with DATABASE_URL set):

    python -m app.bootstrap

A fresh database gets ``schema.sql``. Every start then applies the
idempotent files in ``migrations/`` (``ADD COLUMN IF NOT EXISTS`` ...), so an
existing deployment picks up new tables and columns without data loss.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _first(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


SCHEMA_PATH = _first(_HERE.parent / "schema.sql", _HERE.parents[2] / "schema" / "schema.sql")
MIGRATIONS_DIR = _first(_HERE.parent / "migrations", _HERE.parents[2] / "schema" / "migrations")


def load_schema(path: Path | None = None) -> list[str]:
    """Split a SQL file into executable statements.

    Safe for these files: plain DDL, no dollar-quoted bodies, no semicolons
    inside string literals.
    """
    lines = (path or SCHEMA_PATH).read_text(encoding="utf-8").splitlines()
    code = "\n".join(line for line in lines if not line.strip().startswith("--"))
    return [chunk.strip() for chunk in code.split(";") if chunk.strip()]


def migration_files(directory: Path | None = None) -> list[Path]:
    base = directory or MIGRATIONS_DIR
    return sorted(base.glob("*.sql")) if base.is_dir() else []


def already_bootstrapped() -> bool:
    from sqlalchemy import text

    from .db import engine

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'briefings'"
            )
        ).first()
    return row is not None


def main() -> int:
    from sqlalchemy import text

    from .db import engine

    if not already_bootstrapped():
        statements = load_schema()
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        print(f"bootstrap: applied {len(statements)} schema statements")
    applied = 0
    for path in migration_files():
        # Enum additions cannot share a transaction with their first use.
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for statement in load_schema(path):
                conn.execute(text(statement))
                applied += 1
    print(f"bootstrap: applied {applied} idempotent migration statements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
