#!/usr/bin/env python
"""Explicit migration for permanent student login and single-use activation links.

Default mode is read-only. Pass --apply only after a reviewed backup and schema audit.
"""
from __future__ import annotations

import argparse
import os

from sqlalchemy import DateTime, Integer, create_engine, inspect, text


DDL = (
    """CREATE TABLE IF NOT EXISTS student_access_credentials (
        student_id VARCHAR(32) PRIMARY KEY,
        password_hash VARCHAR(255) NOT NULL,
        failed_login_count INT NOT NULL DEFAULT 0,
        locked_until DATETIME NULL,
        last_login_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_student_access_credentials_student
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS student_access_tokens (
        token_hash CHAR(64) PRIMARY KEY,
        student_id VARCHAR(32) NOT NULL,
        expires_at DATETIME NOT NULL,
        used_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_student_access_tokens_student
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        INDEX idx_student_access_token_student(student_id),
        INDEX idx_student_access_token_expiry(expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)

REQUIRED = {
    "student_access_credentials": {
        "student_id", "password_hash", "failed_login_count", "locked_until",
        "last_login_at", "created_at", "updated_at",
    },
    "student_access_tokens": {
        "token_hash", "student_id", "expires_at", "used_at", "created_at",
    },
}



COLUMN_SPECS = {
    "student_access_credentials": {
        "student_id": ("varchar", 32),
        "password_hash": ("varchar", 255),
        "failed_login_count": ("integer", None),
        "locked_until": ("datetime", None),
        "last_login_at": ("datetime", None),
        "created_at": ("datetime", None),
        "updated_at": ("datetime", None),
    },
    "student_access_tokens": {
        "token_hash": ("char", 64),
        "student_id": ("varchar", 32),
        "expires_at": ("datetime", None),
        "used_at": ("datetime", None),
        "created_at": ("datetime", None),
    },
}

EXPECTED_PRIMARY_KEYS = {
    "student_access_credentials": ["student_id"],
    "student_access_tokens": ["token_hash"],
}

EXPECTED_INDEXES = {
    "student_access_tokens": {
        "idx_student_access_token_student": ["student_id"],
        "idx_student_access_token_expiry": ["expires_at"],
    },
}


def _matches_column_type(actual_type, expected):
    kind, length = expected
    type_name = actual_type.__class__.__name__.upper()

    if kind == "varchar":
        return type_name == "VARCHAR" and actual_type.length == length
    if kind == "char":
        return type_name == "CHAR" and actual_type.length == length
    if kind == "integer":
        return isinstance(actual_type, Integer)
    if kind == "datetime":
        return isinstance(actual_type, DateTime)

    return False


def audit(database_url: str) -> dict:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        if "students" not in tables:
            raise RuntimeError("Required parent table 'students' is missing.")

        parent_columns = {
            column["name"]: column
            for column in inspector.get_columns("students")
        }
        if "student_id" not in parent_columns:
            raise RuntimeError("Required parent column students.student_id is missing.")

        parent_type = parent_columns["student_id"]["type"]
        parent_type_valid = _matches_column_type(parent_type, ("varchar", 32))

        result = {
            "parent": {
                "student_id_type": str(parent_type),
                "student_id_valid": parent_type_valid,
            },
            "tables": {},
        }

        for table, required_columns in REQUIRED.items():
            if table not in tables:
                result["tables"][table] = {
                    "exists": False,
                    "missing_columns": sorted(required_columns),
                    "invalid_columns": {},
                    "primary_key_valid": False,
                    "foreign_key_valid": False,
                    "missing_indexes": sorted(
                        EXPECTED_INDEXES.get(table, {})
                    ),
                    "issues": ["table_missing"],
                }
                continue

            column_details = {
                column["name"]: column
                for column in inspector.get_columns(table)
            }
            actual_columns = set(column_details)
            missing_columns = sorted(required_columns - actual_columns)

            invalid_columns = {}
            for name, expected in COLUMN_SPECS[table].items():
                if name not in column_details:
                    continue

                actual_type = column_details[name]["type"]
                if not _matches_column_type(actual_type, expected):
                    invalid_columns[name] = {
                        "expected": f"{expected[0]}({expected[1]})"
                        if expected[1] is not None else expected[0],
                        "actual": str(actual_type),
                    }

            actual_primary_key = (
                inspector.get_pk_constraint(table).get("constrained_columns") or []
            )
            primary_key_valid = (
                actual_primary_key == EXPECTED_PRIMARY_KEYS[table]
            )

            foreign_keys = inspector.get_foreign_keys(table)
            foreign_key_valid = any(
                fk.get("constrained_columns") == ["student_id"]
                and fk.get("referred_table") == "students"
                and fk.get("referred_columns") == ["student_id"]
                and (fk.get("options") or {}).get("ondelete", "").upper() == "CASCADE"
                for fk in foreign_keys
            )

            actual_indexes = inspector.get_indexes(table)
            missing_indexes = []
            for index_name, expected_columns in EXPECTED_INDEXES.get(table, {}).items():
                found = any(
                    index.get("name") == index_name
                    and index.get("column_names") == expected_columns
                    for index in actual_indexes
                )
                if not found:
                    missing_indexes.append(index_name)

            issues = []
            if missing_columns:
                issues.append("missing_columns")
            if invalid_columns:
                issues.append("invalid_column_types")
            if not primary_key_valid:
                issues.append("primary_key_mismatch")
            if not foreign_key_valid:
                issues.append("foreign_key_missing_or_incompatible")
            if missing_indexes:
                issues.append("missing_indexes")
            if not parent_type_valid:
                issues.append("parent_student_id_type_incompatible")

            result["tables"][table] = {
                "exists": True,
                "missing_columns": missing_columns,
                "invalid_columns": invalid_columns,
                "primary_key_valid": primary_key_valid,
                "foreign_key_valid": foreign_key_valid,
                "missing_indexes": missing_indexes,
                "issues": issues,
            }

        return result
    finally:
        engine.dispose()


def apply(database_url: str) -> None:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    try:
        with engine.begin() as connection:
            parent = connection.execute(text("SHOW TABLES LIKE 'students'")).first()
            if not parent:
                raise RuntimeError("Required parent table 'students' is missing.")
            columns = {
                row[0] for row in connection.execute(text("SHOW COLUMNS FROM students")).all()
            }
            if "student_id" not in columns:
                raise RuntimeError("Required parent column students.student_id is missing.")
            for statement in DDL:
                connection.execute(text(statement))
        report = audit(database_url)
        incomplete = {
            table: info
            for table, info in report["tables"].items()
            if info["issues"]
        }
        if not report["parent"]["student_id_valid"] or incomplete:
            raise RuntimeError(
                "Post-migration verification failed: "
                f"parent={report['parent']}, tables={incomplete}"
            )
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create the two access tables. This is a database write; backup and approval are required.",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Supply --database-url or set DATABASE_URL locally; never paste credentials into chat.")

    if args.apply:
        apply(args.database_url)
        print("Migration 006 applied and verified.")
    else:
        print("READ-ONLY AUDIT — no database changes were made.")
        print(audit(args.database_url))
        print("Pass --apply only after backup, schema review, and explicit approval.")


if __name__ == "__main__":
    main()
