#!/usr/bin/env python
"""Explicit migration for tests.monitoring_mode.

Run --dry-run first. Only --apply modifies the database.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, inspect, text


VALID_MODES = ("off", "optional", "required")


def _normalise_default(value):
    if value is None:
        return None

    value = str(value).strip()
    value = value.strip("()")
    value = value.strip("'\"")
    return value.lower()


def inspect_migration(engine):
    inspector = inspect(engine)

    if not inspector.has_table("tests"):
        raise RuntimeError(
            "The tests table does not exist; apply foundation migrations first."
        )

    columns = {
        column["name"]: column
        for column in inspector.get_columns("tests")
    }

    column = columns.get("monitoring_mode")

    if column is None:
        return {
            "column_exists": False,
            "invalid_rows": None,
            "needs_schema_repair": False,
        }

    column_type = str(column["type"]).upper().replace(" ", "")

    if not re.fullmatch(r"VARCHAR\(20\)", column_type):
        raise RuntimeError(
            "Incompatible tests.monitoring_mode type: "
            f"{column_type}. Expected VARCHAR(20). "
            "Manual schema review is required."
        )

    default = _normalise_default(column.get("default"))
    needs_schema_repair = (
        column.get("nullable", True)
        or default != "off"
    )

    with engine.connect() as db:
        invalid_rows = db.execute(
            text(
                "SELECT COUNT(*) FROM tests "
                "WHERE monitoring_mode IS NULL "
                "OR monitoring_mode NOT IN ('off', 'optional', 'required')"
            )
        ).scalar_one()

    return {
        "column_exists": True,
        "invalid_rows": invalid_rows,
        "needs_schema_repair": needs_schema_repair,
    }


def apply_migration(engine):
    plan = inspect_migration(engine)

    # Fail before changing data if the existing schema cannot be repaired.
    if (
        plan["column_exists"]
        and plan["needs_schema_repair"]
        and engine.dialect.name != "mysql"
    ):
        raise RuntimeError(
            "The existing column needs a schema repair, but automatic "
            "schema repair is supported only for MySQL. "
            "No data changes were made. Review the schema manually."
        )

    if not plan["column_exists"]:
        with engine.begin() as db:
            db.execute(
                text(
                    "ALTER TABLE tests "
                    "ADD COLUMN monitoring_mode "
                    "VARCHAR(20) NOT NULL DEFAULT 'off'"
                )
            )

    with engine.begin() as db:
        result = db.execute(
            text(
                "UPDATE tests SET monitoring_mode='off' "
                "WHERE monitoring_mode IS NULL "
                "OR monitoring_mode NOT IN ('off', 'optional', 'required')"
            )
        )

    schema_repaired = False

    if plan["column_exists"] and plan["needs_schema_repair"]:
        with engine.begin() as db:
            db.execute(
                text(
                    "ALTER TABLE tests "
                    "MODIFY COLUMN monitoring_mode "
                    "VARCHAR(20) NOT NULL DEFAULT 'off'"
                )
            )

        schema_repaired = True

    return {
        "column_added": not plan["column_exists"],
        "schema_repaired": schema_repaired,
        "rows_normalized": result.rowcount,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (defaults to DATABASE_URL).",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)

    database_url = args.database_url or os.getenv("DATABASE_URL")

    if not database_url:
        from database import DATABASE_URL
        database_url = DATABASE_URL

    if not database_url:
        parser.error("Provide --database-url or set DATABASE_URL.")

    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        if args.dry_run:
            plan = inspect_migration(engine)

            if not plan["column_exists"]:
                print(
                    "Would add tests.monitoring_mode "
                    "VARCHAR(20) NOT NULL DEFAULT 'off'."
                )
            else:
                print("monitoring_mode column exists.")
                print(
                    f"Rows requiring normalization: {plan['invalid_rows']}"
                )
                print(
                    "Schema repair required: "
                    f"{plan['needs_schema_repair']}"
                )

            print("Dry-run completed. No database changes made.")

        else:
            result = apply_migration(engine)
            print(f"Column added: {result['column_added']}")
            print(f"Schema repaired: {result['schema_repaired']}")
            print(f"Rows normalized: {result['rows_normalized']}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
