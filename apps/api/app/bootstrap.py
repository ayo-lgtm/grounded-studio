"""Create a fresh database from schema.sql. Run once per database.

Usage (any platform, with DATABASE_URL set):

    python -m app.bootstrap

Exits 0 without changes when the schema is already present.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def load_schema(path: Path | None = None) -> list[str]:
    """Split schema.sql into executable statements.

    Safe for this schema: plain DDL, no dollar-quoted bodies, no
    semicolons inside string literals.
    """
    lines = (path or SCHEMA_PATH).read_text(encoding="utf-8").splitlines()
    code = "\n".join(line for line in lines if not line.strip().startswith("--"))
    return [chunk.strip() for chunk in code.split(";") if chunk.strip()]


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
    if already_bootstrapped():
        print("bootstrap: schema already present, nothing to do")
        return 0
    from sqlalchemy import text

    from .db import engine

    statements = load_schema()
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    print(f"bootstrap: applied {len(statements)} statements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
