"""Database migration helpers for exam monitoring settings."""

import os

from sqlalchemy import inspect, text

from database import engine


MONITORING_MODES = {"off", "optional", "required"}


def ensure_exam_monitoring_schema() -> None:
    """Bootstrap local schema, but never mutate the production schema at startup."""
    if os.getenv("RENDER"):
        columns = {column["name"] for column in inspect(engine).get_columns("tests")}
        if "monitoring_mode" not in columns:
            raise RuntimeError(
                "Production database is missing tests.monitoring_mode. "
                "Apply the reviewed database migration before deploying this version."
            )
        return

    with engine.begin() as connection:
        column = connection.execute(
            text("SHOW COLUMNS FROM tests LIKE 'monitoring_mode'")
        ).first()
        if not column:
            connection.execute(
                text(
                    "ALTER TABLE tests "
                    "ADD COLUMN monitoring_mode VARCHAR(20) NOT NULL DEFAULT 'off' "
                    "AFTER status"
                )
            )

        connection.execute(
            text(
                "UPDATE tests SET monitoring_mode='off' "
                "WHERE monitoring_mode IS NULL "
                "OR monitoring_mode NOT IN ('off','optional','required')"
            )
        )
