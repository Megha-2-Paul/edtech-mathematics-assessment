"""Shared, parameterized access to the migration ledger."""
from __future__ import annotations

from sqlalchemy import inspect, text


VALID_STATUSES = {"pending", "running", "applied", "failed", "adopted"}
LEDGER_TABLE = "schema_migrations"


def read_ledger(engine) -> list[dict]:
    """Return ledger records without changing the database."""
    if not inspect(engine).has_table(LEDGER_TABLE):
        return []
    columns = {c["name"] for c in inspect(engine).get_columns(LEDGER_TABLE)}
    if not {"migration_id", "applied_at"}.issubset(columns):
        raise RuntimeError("Incompatible schema_migrations ledger structure.")
    selected = ["migration_id", "applied_at"]
    selected.extend(
        name for name in (
            "status", "checksum", "started_at", "completed_at",
            "error_summary", "execution_version",
        ) if name in columns
    )
    statement = "SELECT " + ", ".join(selected) + " FROM schema_migrations ORDER BY migration_id"
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(statement)).mappings()]


def record_migration(
    engine,
    migration_id: str,
    status: str,
    *,
    checksum: str | None = None,
    started_at=None,
    completed_at=None,
    error_summary: str | None = None,
    execution_version: str | None = None,
) -> None:
    """Insert or update one record; callers must verify postconditions first."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported migration status: {status}")
    if not migration_id or len(migration_id) > 100:
        raise ValueError("migration_id must contain 1 to 100 characters.")
    if checksum is not None and (
        len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum.lower())
    ):
        raise ValueError("checksum must be a 64-character hexadecimal SHA-256 digest.")

    columns = {c["name"] for c in inspect(engine).get_columns(LEDGER_TABLE)}
    required_columns = {
        "migration_id", "applied_at", "status", "checksum", "started_at",
        "completed_at", "error_summary", "execution_version",
    }
    missing_columns = required_columns - columns
    if missing_columns:
        raise RuntimeError(
            "Migration ledger upgrade is required before recording status; "
            f"missing columns: {', '.join(sorted(missing_columns))}."
        )

    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO schema_migrations (
                    migration_id, status, checksum, started_at, completed_at,
                    error_summary, execution_version
                ) VALUES (
                    :migration_id, :status, :checksum, :started_at, :completed_at,
                    :error_summary, :execution_version
                )
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    checksum = COALESCE(VALUES(checksum), checksum),
                    started_at = COALESCE(VALUES(started_at), started_at),
                    completed_at = COALESCE(VALUES(completed_at), completed_at),
                    error_summary = VALUES(error_summary),
                    execution_version = COALESCE(VALUES(execution_version), execution_version)
            """) if engine.dialect.name == "mysql" else text("""
                INSERT INTO schema_migrations (
                    migration_id, status, checksum, started_at, completed_at,
                    error_summary, execution_version
                ) VALUES (
                    :migration_id, :status, :checksum, :started_at, :completed_at,
                    :error_summary, :execution_version
                )
                ON CONFLICT(migration_id) DO UPDATE SET
                    status = excluded.status,
                    checksum = COALESCE(excluded.checksum, schema_migrations.checksum),
                    started_at = COALESCE(excluded.started_at, schema_migrations.started_at),
                    completed_at = COALESCE(excluded.completed_at, schema_migrations.completed_at),
                    error_summary = excluded.error_summary,
                    execution_version = COALESCE(excluded.execution_version, schema_migrations.execution_version)
            """),
            {
                "migration_id": migration_id,
                "status": status,
                "checksum": checksum,
                "started_at": started_at,
                "completed_at": completed_at,
                "error_summary": error_summary,
                "execution_version": execution_version,
            },
        )
