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


def _validate_legacy_ledger(inspector) -> None:
    columns = {
        column["name"]: column
        for column in inspector.get_columns("schema_migrations")
    }
    primary_key = inspector.get_pk_constraint("schema_migrations").get(
        "constrained_columns"
    ) or []
    required = {"migration_id", "applied_at"}
    missing = required - columns.keys()
    if missing:
        raise RuntimeError(
            "Incompatible schema_migrations ledger; missing required "
            f"columns: {', '.join(sorted(missing))}. No columns added."
        )

    migration_id_type = str(columns["migration_id"]["type"]).upper().replace(" ", "")
    applied_at_type = str(columns["applied_at"]["type"]).upper().replace(" ", "")
    if (
        "migration_id" not in primary_key
        or not migration_id_type.startswith("VARCHAR(100)")
        or "DATETIME" not in applied_at_type
        or columns["applied_at"].get("nullable", True)
    ):
        raise RuntimeError(
            "Incompatible schema_migrations ledger definition; expected "
            "migration_id VARCHAR(100) PRIMARY KEY and applied_at DATETIME NOT NULL. "
            "No columns added."
        )


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

    _validate_legacy_ledger(inspector)

    existing = {
        column["name"]
        for column in inspector.get_columns("schema_migrations")
    }
    added = []
    for name, definition in LEDGER_COLUMNS.items():
        if name in existing:
            continue
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
