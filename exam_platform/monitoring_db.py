"""Database migration helpers for exam monitoring settings."""

from sqlalchemy import text

from database import engine


MONITORING_MODES = {"off", "optional", "required"}


def ensure_exam_monitoring_schema() -> None:
    """Add the test monitoring column safely to existing databases."""
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
