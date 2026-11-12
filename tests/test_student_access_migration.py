import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "question_bank"
    / "migrations"
    / "006_student_access.py"
)

SPEC = importlib.util.spec_from_file_location(
    "student_access_migration",
    MIGRATION_PATH,
)
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def _create_database(
    tmp_path,
    *,
    parent_type="VARCHAR(32)",
    password_hash_type="VARCHAR(255)",
    credential_pk=True,
    token_pk=True,
    cascade=True,
    include_indexes=True,
    include_tokens=True,
    omit_credential_column=None,
):
    database_path = tmp_path / "migration_audit.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)

    try:
        with engine.begin() as connection:
            connection.execute(text(
                f"CREATE TABLE students ("
                f"student_id {parent_type} PRIMARY KEY)"
            ))

            credential_columns = [
                f"student_id VARCHAR(32) {'PRIMARY KEY' if credential_pk else 'NOT NULL'}",
                f"password_hash {password_hash_type} NOT NULL",
                "failed_login_count INTEGER NOT NULL DEFAULT 0",
                "locked_until DATETIME NULL",
                "last_login_at DATETIME NULL",
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            ]

            if omit_credential_column:
                credential_columns = [
                    column for column in credential_columns
                    if not column.startswith(omit_credential_column + " ")
                ]

            delete_rule = "CASCADE" if cascade else "RESTRICT"
            credential_columns.append(
                "FOREIGN KEY (student_id) REFERENCES "
                f"students(student_id) ON DELETE {delete_rule}"
            )

            connection.execute(text(
                "CREATE TABLE student_access_credentials ("
                + ", ".join(credential_columns)
                + ")"
            ))

            if include_tokens:
                token_columns = [
                    f"token_hash CHAR(64) {'PRIMARY KEY' if token_pk else 'NOT NULL'}",
                    "student_id VARCHAR(32) NOT NULL",
                    "expires_at DATETIME NOT NULL",
                    "used_at DATETIME NULL",
                    "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
                    "FOREIGN KEY (student_id) REFERENCES "
                    f"students(student_id) ON DELETE {delete_rule}",
                ]

                connection.execute(text(
                    "CREATE TABLE student_access_tokens ("
                    + ", ".join(token_columns)
                    + ")"
                ))

                if include_indexes:
                    connection.execute(text(
                        "CREATE INDEX idx_student_access_token_student "
                        "ON student_access_tokens(student_id)"
                    ))
                    connection.execute(text(
                        "CREATE INDEX idx_student_access_token_expiry "
                        "ON student_access_tokens(expires_at)"
                    ))
    finally:
        engine.dispose()

    return database_url


def test_audit_accepts_valid_schema(tmp_path):
    database_url = _create_database(tmp_path)

    report = MIGRATION.audit(database_url)

    assert report["parent"]["student_id_valid"] is True
    assert report["tables"]["student_access_credentials"]["issues"] == []
    assert report["tables"]["student_access_tokens"]["issues"] == []


def test_audit_detects_missing_table(tmp_path):
    database_url = _create_database(tmp_path, include_tokens=False)

    report = MIGRATION.audit(database_url)

    token_report = report["tables"]["student_access_tokens"]
    assert token_report["exists"] is False
    assert "table_missing" in token_report["issues"]


def test_audit_detects_missing_column(tmp_path):
    database_url = _create_database(
        tmp_path,
        omit_credential_column="last_login_at",
    )

    report = MIGRATION.audit(database_url)

    credential_report = report["tables"]["student_access_credentials"]
    assert "last_login_at" in credential_report["missing_columns"]
    assert "missing_columns" in credential_report["issues"]


def test_audit_detects_incorrect_column_length(tmp_path):
    database_url = _create_database(
        tmp_path,
        password_hash_type="VARCHAR(100)",
    )

    report = MIGRATION.audit(database_url)

    credential_report = report["tables"]["student_access_credentials"]
    assert "password_hash" in credential_report["invalid_columns"]
    assert "invalid_column_types" in credential_report["issues"]


def test_audit_detects_incorrect_primary_key(tmp_path):
    database_url = _create_database(tmp_path, credential_pk=False)

    report = MIGRATION.audit(database_url)

    credential_report = report["tables"]["student_access_credentials"]
    assert credential_report["primary_key_valid"] is False
    assert "primary_key_mismatch" in credential_report["issues"]


def test_audit_detects_missing_cascade_foreign_key(tmp_path):
    database_url = _create_database(tmp_path, cascade=False)

    report = MIGRATION.audit(database_url)

    credential_report = report["tables"]["student_access_credentials"]
    assert credential_report["foreign_key_valid"] is False
    assert "foreign_key_missing_or_incompatible" in credential_report["issues"]


def test_audit_detects_missing_required_index(tmp_path):
    database_url = _create_database(tmp_path, include_indexes=False)

    report = MIGRATION.audit(database_url)

    token_report = report["tables"]["student_access_tokens"]
    assert set(token_report["missing_indexes"]) == {
        "idx_student_access_token_student",
        "idx_student_access_token_expiry",
    }
    assert "missing_indexes" in token_report["issues"]


def test_audit_detects_incompatible_parent_student_id_type(tmp_path):
    database_url = _create_database(tmp_path, parent_type="TEXT")

    report = MIGRATION.audit(database_url)

    assert report["parent"]["student_id_valid"] is False
    assert "parent_student_id_type_incompatible" in (
        report["tables"]["student_access_credentials"]["issues"]
    )


def test_audit_detects_incorrect_token_primary_key(tmp_path):
    database_url = _create_database(tmp_path, token_pk=False)

    report = MIGRATION.audit(database_url)

    token_report = report["tables"]["student_access_tokens"]
    assert token_report["primary_key_valid"] is False
    assert "primary_key_mismatch" in token_report["issues"]

