"""Add migration execution metadata to the shared schema_migrations ledger.

This migration is additive and safe to rerun. It preserves the original
migration_id/applied_at contract used by migrations 001 and 002.
"""
from __future__ import annotations

from sqlalchemy import inspect, text


LEDGER_COLUMNS = {
    "status": "VARCHAR(20) NOT NULL DEFAULT 'applied'",
    "checksum": "CHAR(64) NULL",
    "started_at": "DATETIME NULL",
    "completed_at": "DATETIME NULL",
    "error_summary": "TEXT NULL",
    "execution_version": "VARCHAR(30) NULL",
}


def upgrade_ledger(engine) -> list[str]:
    """Create or compatibly extend schema_migrations; return added columns."""
    inspector = inspect(engine)

    if not inspector.has_table("schema_migrations"):
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE schema_migrations (
                    migration_id VARCHAR(100) PRIMARY KEY,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
        inspector = inspect(engine)

    existing = {
        column["name"]: column
        for column in inspector.get_columns("schema_migrations")
    }
    required = {"migration_id", "applied_at"}
    missing_required = required - existing.keys()
    if missing_required:
        raise RuntimeError(
            "Incompatible schema_migrations ledger; missing required "
            f"columns: {', '.join(sorted(missing_required))}. No columns added."
        )

    added = []
    for name, definition in LEDGER_COLUMNS.items():
        if name in existing:
            continue
        # Column names and definitions are fixed constants, never user input.
        with engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE schema_migrations ADD COLUMN {name} {definition}")
            )
        added.append(name)
    return added


def main() -> None:
    import os
    from sqlalchemy import create_engine

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("Set DATABASE_URL to the intended LOCAL database.")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        added = upgrade_ledger(engine)
        print("Added ledger columns: " + (", ".join(added) if added else "none"))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
