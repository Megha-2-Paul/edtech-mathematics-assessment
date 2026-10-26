#!/usr/bin/env python
"""Explicit migration for permanent student login and single-use activation links.

Default mode is read-only. Pass --apply only after a reviewed backup and schema audit.
"""
from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, inspect, text


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


def audit(database_url: str) -> dict:
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "students" not in tables:
            raise RuntimeError("Required parent table 'students' is missing.")
        student_columns = {column["name"] for column in inspector.get_columns("students")}
        if "student_id" not in student_columns:
            raise RuntimeError("Required parent column students.student_id is missing.")

        result = {"tables": {}}
        for table, columns in REQUIRED.items():
            if table not in tables:
                result["tables"][table] = {"exists": False, "missing_columns": sorted(columns)}
                continue
            actual = {column["name"] for column in inspector.get_columns(table)}
            result["tables"][table] = {
                "exists": True,
                "missing_columns": sorted(columns - actual),
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
            table: info for table, info in report["tables"].items()
            if not info["exists"] or info["missing_columns"]
        }
        if incomplete:
            raise RuntimeError(f"Post-migration verification failed: {incomplete}")
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
