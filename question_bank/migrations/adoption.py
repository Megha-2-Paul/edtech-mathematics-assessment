"""Read-only verification of legacy migration postconditions.

This module never writes to the database and deliberately reports UNKNOWN when
schema inspection alone cannot prove a migration's data effects.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from .manifest import MIGRATIONS


VERIFIED_APPLIED = "VERIFIED_APPLIED"
VERIFIED_NOT_APPLIED = "VERIFIED_NOT_APPLIED"
PARTIALLY_APPLIED = "PARTIALLY_APPLIED"
CONFLICTING = "CONFLICTING"
UNKNOWN = "UNKNOWN"


def _columns(inspector, table: str) -> set[str]:
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _index_names(inspector, table: str) -> set[str]:
    if not inspector.has_table(table):
        return set()
    return {index["name"] for index in inspector.get_indexes(table)}


def _table_state(inspector, required: set[str]) -> tuple[int, int]:
    return sum(inspector.has_table(table) for table in required), len(required)



def _schema_column_matches(
    inspector,
    table: str,
    name: str,
    accepted_types: tuple[str, ...] | str,
    nullable: bool | None,
    accepted_defaults: tuple[str, ...] | None = None,
    autoincrement: bool | None = None,
) -> bool:
    if not inspector.has_table(table):
        return False

    column = next(
        (item for item in inspector.get_columns(table) if item["name"] == name),
        None,
    )
    if column is None:
        return False

    if isinstance(accepted_types, str):
        accepted_types = (accepted_types,)

    actual_type = str(column["type"]).upper().replace(" ", "")
    expected_types = {
        value.upper().replace(" ", "") for value in accepted_types
    }
    if actual_type not in expected_types:
        return False

    if nullable is not None and bool(column.get("nullable", True)) != nullable:
        return False

    if accepted_defaults is not None:
        default = column.get("default")
        if default is None:
            return False
        normalized = str(default).strip().strip("()").strip("'").strip('"').lower()
        expected_defaults = {value.lower() for value in accepted_defaults}
        if normalized not in expected_defaults:
            return False

    if autoincrement is not None:
        if bool(column.get("autoincrement")) != autoincrement:
            return False

    return True


def _column_default_contains(inspector, table: str, name: str, clause: str) -> bool:
    if not inspector.has_table(table):
        return False

    column = next(
        (item for item in inspector.get_columns(table) if item["name"] == name),
        None,
    )
    if column is None:
        return False

    default = column.get("default")
    return default is not None and clause.upper() in str(default).upper()


def _index_matches(inspector, table: str, name: str, columns: tuple[str, ...]) -> bool:
    if not inspector.has_table(table):
        return False

    for index in inspector.get_indexes(table):
        if index["name"] == name:
            return tuple(index.get("column_names") or ()) == columns

    return False


def _primary_key_matches(inspector, table: str, columns: tuple[str, ...]) -> bool:
    if not inspector.has_table(table):
        return False
    primary_key = inspector.get_pk_constraint(table).get("constrained_columns") or []
    return tuple(primary_key) == columns


def _unique_columns_match(inspector, table: str, columns: tuple[str, ...]) -> bool:
    if not inspector.has_table(table):
        return False

    for constraint in inspector.get_unique_constraints(table):
        if tuple(constraint.get("column_names") or ()) == columns:
            return True

    for index in inspector.get_indexes(table):
        if index.get("unique") and tuple(index.get("column_names") or ()) == columns:
            return True

    return False


def _foreign_key_matches(
    inspector,
    table: str,
    columns: tuple[str, ...],
    referred_table: str,
    referred_columns: tuple[str, ...],
    ondelete: str,
) -> bool:
    if not inspector.has_table(table):
        return False

    for foreign_key in inspector.get_foreign_keys(table):
        options = foreign_key.get("options") or {}
        if (
            tuple(foreign_key.get("constrained_columns") or ()) == columns
            and foreign_key.get("referred_table") == referred_table
            and tuple(foreign_key.get("referred_columns") or ()) == referred_columns
            and str(options.get("ondelete", "")).upper() == ondelete.upper()
        ):
            return True

    if inspector.bind.dialect.name == "sqlite":
        with inspector.bind.connect() as connection:
            rows = connection.exec_driver_sql(
                f'PRAGMA foreign_key_list("{table}")'
            ).fetchall()
        return any(
            row[2] == referred_table
            and row[3] == columns[0]
            and row[4] == referred_columns[0]
            and str(row[6]).upper() == ondelete.upper()
            for row in rows
        )

    return False


def _verify(engine, migration_id: str) -> tuple[str, str]:
    inspector = inspect(engine)

    if migration_id == "001_question_bank_foundation":
        if not inspector.has_table("questions") or not inspector.has_table("question_assets"):
            return UNKNOWN, "Base questions/question_assets tables are absent; foundation state cannot be assessed."
        required_tables = {
            "source_papers", "question_occurrences", "question_groups",
            "question_parts", "question_extraction_runs",
            "question_extraction_results", "question_verifications",
            "extraction_jobs", "extraction_providers", "extraction_feedback",
        }
        present, total = _table_state(inspector, required_tables)
        question_columns = {"source_type", "verification_status", "canonical_question_id"}
        asset_columns = {"page_number", "bbox_json", "asset_role", "source_asset_id"}
        has_columns = (
            question_columns.issubset(_columns(inspector, "questions"))
            and asset_columns.issubset(_columns(inspector, "question_assets"))
        )
        required_indexes = {
            "idx_questions_source_type", "idx_questions_verification_status",
            "idx_questions_canonical",
        }
        question_definitions = (
            _schema_column_matches(
                inspector, "questions", "source_type", "VARCHAR(20)", False,
                ("MANUAL", "manual"),
            )
            and _schema_column_matches(
                inspector, "questions", "verification_status", "VARCHAR(30)", False,
                ("VERIFIED",),
            )
            and _schema_column_matches(
                inspector, "questions", "canonical_question_id", "VARCHAR(40)", True,
            )
        )
        asset_definitions = (
            _schema_column_matches(
                inspector, "question_assets", "page_number", "INTEGER", True,
            )
            and _schema_column_matches(
                inspector, "question_assets", "bbox_json", "TEXT", True,
            )
            and _schema_column_matches(
                inspector, "question_assets", "asset_role", "VARCHAR(50)", True,
            )
            and _schema_column_matches(
                inspector, "question_assets", "source_asset_id", "VARCHAR(70)", True,
            )
        )
        index_definitions = all((
            _index_matches(inspector, "questions", "idx_questions_source_type", ("source_type",)),
            _index_matches(inspector, "questions", "idx_questions_verification_status", ("verification_status",)),
            _index_matches(inspector, "questions", "idx_questions_canonical", ("canonical_question_id",)),
            _index_matches(inspector, "question_assets", "idx_question_asset_page", ("question_id", "page_number")),
        ))
        has_indexes = required_indexes.issubset(_index_names(inspector, "questions"))
        has_indexes = has_indexes and "idx_question_asset_page" in _index_names(
            inspector, "question_assets"
        )

        if present == total and has_columns and has_indexes:
            if not question_definitions or not asset_definitions or not index_definitions:
                return CONFLICTING, "Foundation objects exist but one or more column or index definitions are incompatible."
            return VERIFIED_APPLIED, "Foundation tables, column definitions, and index definitions are verified."
        if present == 0 and not has_columns and not has_indexes:
            return VERIFIED_NOT_APPLIED, "Foundation tables, columns, and indexes are absent."
        return PARTIALLY_APPLIED, "Only part of the foundation schema is present."

    if migration_id == "002_canonical_question_ingestion":
        if not inspector.has_table("questions"):
            return UNKNOWN, "Cannot inspect question backfill without questions table."
        if not inspector.has_table("question_solutions"):
            return VERIFIED_NOT_APPLIED, "question_solutions table is absent."
        columns = _columns(inspector, "questions")
        if "canonical_question_id" not in columns:
            return PARTIALLY_APPLIED, "question_solutions exists but canonical ID column is absent."

        required_solution_columns = {
            "question_solution_id", "question_id", "solution_content",
            "marking_scheme", "version", "verified", "source_type",
            "created_at", "updated_at",
        }
        solution_columns = _columns(inspector, "question_solutions")
        if not required_solution_columns.issubset(solution_columns):
            return PARTIALLY_APPLIED, "question_solutions is missing required columns."

        definitions_ok = all((
            _schema_column_matches(
                inspector,
                "question_solutions",
                "question_solution_id",
                ("BIGINT", "INTEGER"),
                None,
                autoincrement=(
                    True if inspector.bind.dialect.name == "mysql" else None
                ),
            ),
            _schema_column_matches(inspector, "question_solutions", "question_id", ("VARCHAR(40)",), False),
            _schema_column_matches(inspector, "question_solutions", "solution_content", ("LONGTEXT", "TEXT"), True),
            _schema_column_matches(inspector, "question_solutions", "marking_scheme", ("LONGTEXT", "TEXT"), True),
            _schema_column_matches(inspector, "question_solutions", "version", ("INTEGER",), False, ("1",)),
            _schema_column_matches(inspector, "question_solutions", "verified", ("BOOLEAN", "BOOL", "TINYINT(1)"), False, ("0", "false")),
            _schema_column_matches(inspector, "question_solutions", "source_type", ("VARCHAR(30)",), False, ("extracted",)),
            _schema_column_matches(inspector, "question_solutions", "created_at", ("DATETIME",), False, ("CURRENT_TIMESTAMP",)),
            _schema_column_matches(
                inspector,
                "question_solutions",
                "updated_at",
                ("DATETIME",),
                False,
                ("CURRENT_TIMESTAMP",),
            )
            and (
                inspector.bind.dialect.name != "mysql"
                or _column_default_contains(
                    inspector,
                    "question_solutions",
                    "updated_at",
                    "ON UPDATE CURRENT_TIMESTAMP",
                )
            ),
        ))
        constraints_ok = (
            _primary_key_matches(inspector, "question_solutions", ("question_solution_id",))
            and _unique_columns_match(inspector, "question_solutions", ("question_id", "version"))
            and _foreign_key_matches(
                inspector, "question_solutions", ("question_id",),
                "questions", ("question_id",), "CASCADE",
            )
            and _index_matches(
                inspector, "question_solutions",
                "idx_question_solution_question", ("question_id",),
            )
        )
        if not definitions_ok or not constraints_ok:
            return CONFLICTING, "question_solutions exists but its column definitions or constraints are incompatible."

        with engine.connect() as connection:
            missing = connection.execute(text(
                "SELECT COUNT(*) FROM questions "
                "WHERE canonical_question_id IS NULL OR canonical_question_id = ''"
            )).scalar_one()
        if missing:
            return PARTIALLY_APPLIED, "Some questions still lack canonical_question_id."
        return VERIFIED_APPLIED, "Solution schema and canonical question ID backfill are verified."

    if migration_id == "003_canonical_math_taxonomy":
        required = {"canonical_subjects", "canonical_chapters", "syllabus_units", "syllabus_chapters"}
        present, total = _table_state(inspector, required)
        if present == total:
            return UNKNOWN, "Taxonomy tables exist; taxonomy seed/data postconditions need source-level verification."
        if present == 0:
            return VERIFIED_NOT_APPLIED, "Legacy taxonomy tables are absent."
        return PARTIALLY_APPLIED, "Only some legacy taxonomy tables are present."

    if migration_id == "004_student_registration_subject":
        if not inspector.has_table("students"):
            return UNKNOWN, "Base students table is absent; registration migration state cannot be assessed."
        columns = _columns(inspector, "students")
        indexes = _index_names(inspector, "students")
        if "subject" in columns and "idx_students_eligibility" in indexes:
            column_ok = _schema_column_matches(
                inspector, "students", "subject", "VARCHAR(100)", True,
            )
            index_ok = _index_matches(
                inspector,
                "students",
                "idx_students_eligibility",
                ("status", "board", "class_level", "subject"),
            )
            if not column_ok or not index_ok:
                return CONFLICTING, "Registration objects exist but their column or index definitions are incompatible."
            return VERIFIED_APPLIED, "Student subject column and eligibility index definitions are verified."
        if "subject" not in columns and "idx_students_eligibility" not in indexes:
            return VERIFIED_NOT_APPLIED, "Student subject column and eligibility index are absent."
        return PARTIALLY_APPLIED, "Only part of the registration schema is present."

    if migration_id == "005_curriculum_question_reuse":
        if not inspector.has_table("students") or not inspector.has_table("questions"):
            return UNKNOWN, "Base students/questions tables are absent; curriculum migration state cannot be assessed."
        required = {
            "subject_catalog", "curriculum_catalog", "curriculum_units",
            "canonical_concepts", "curriculum_chapters", "question_curriculum_map",
            "student_subject_enrollments",
        }
        present, total = _table_state(inspector, required)
        if present == 0:
            return VERIFIED_NOT_APPLIED, "Curriculum target tables are absent."
        if present < total:
            return PARTIALLY_APPLIED, "Only some curriculum target tables are present."
        return UNKNOWN, "Curriculum tables exist; taxonomy seeds, enrolment backfill, and exact question mappings require data-level verification."

    if migration_id == "006_exam_monitoring_mode":
        if not inspector.has_table("tests"):
            return UNKNOWN, "Base tests table is absent; monitoring migration state cannot be assessed."
        columns = {
            c["name"]: c
            for c in inspector.get_columns("tests")
        } if inspector.has_table("tests") else {}
        column = columns.get("monitoring_mode")
        if column is None:
            return VERIFIED_NOT_APPLIED, "tests.monitoring_mode is absent."
        definition_ok = _schema_column_matches(
            inspector,
            "tests",
            "monitoring_mode",
            "VARCHAR(20)",
            False,
            ("off",),
        )
        if not definition_ok:
            return CONFLICTING, "monitoring_mode exists but its type, nullability, or default is incompatible."

        with engine.connect() as connection:
            invalid = connection.execute(text(
                "SELECT COUNT(*) FROM tests WHERE monitoring_mode IS NULL "
                "OR monitoring_mode NOT IN ('off', 'optional', 'required')"
            )).scalar_one()
        if invalid:
            return PARTIALLY_APPLIED, "monitoring_mode exists but contains invalid or null values."
        return VERIFIED_APPLIED, "monitoring_mode column definition and values are verified."

    if migration_id == "008_migration_ledger_upgrade":
        columns = _columns(inspector, "schema_migrations")
        expected = {
            "migration_id", "applied_at", "status", "checksum", "started_at",
            "completed_at", "error_summary", "execution_version",
        }
        if not columns:
            return VERIFIED_NOT_APPLIED, "Migration ledger is absent."
        if not {"migration_id", "applied_at"}.issubset(columns):
            return CONFLICTING, "Migration ledger is missing its required legacy columns."

        if not expected.issubset(columns):
            return PARTIALLY_APPLIED, "Legacy ledger exists but extension is incomplete."

        definitions_ok = (
            _schema_column_matches(
                inspector, "schema_migrations", "migration_id",
                ("VARCHAR(100)",), None,
            )
            and _primary_key_matches(inspector, "schema_migrations", ("migration_id",))
            and _schema_column_matches(
                inspector, "schema_migrations", "applied_at",
                ("DATETIME",), False, ("CURRENT_TIMESTAMP",),
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "status",
                ("VARCHAR(20)",), False, ("applied",),
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "checksum",
                ("CHAR(64)",), True,
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "started_at",
                ("DATETIME",), True,
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "completed_at",
                ("DATETIME",), True,
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "error_summary",
                ("TEXT",), True,
            )
            and _schema_column_matches(
                inspector, "schema_migrations", "execution_version",
                ("VARCHAR(30)",), True,
            )
        )
        if not definitions_ok:
            return CONFLICTING, "Migration ledger columns exist but one or more definitions are incompatible."

        return VERIFIED_APPLIED, "Migration ledger column definitions and primary key are verified."

    return UNKNOWN, "No postcondition verifier is defined for this migration."


def inspect_legacy_migrations(
    engine, migration_ids: tuple[str, ...] | None = None
) -> list[dict]:
    """Classify migrations using read-only checks; never records adoption."""
    ids = migration_ids or tuple(m.migration_id for m in MIGRATIONS)
    inspector = inspect(engine)
    ledger_columns = _columns(inspector, "schema_migrations")
    ledger = {}
    if "migration_id" in ledger_columns:
        selected = ["migration_id", "applied_at"]
        if "checksum" in ledger_columns:
            selected.append("checksum")
        if "status" in ledger_columns:
            selected.append("status")
        with engine.connect() as connection:
            ledger = {
                row["migration_id"]: dict(row)
                for row in connection.execute(
                    text("SELECT " + ", ".join(selected) + " FROM schema_migrations")
                ).mappings()
            }

    manifest = {migration.migration_id: migration for migration in MIGRATIONS}
    results = []
    for migration_id in ids:
        state, evidence = _verify(engine, migration_id)
        record = ledger.get(migration_id)
        migration = manifest.get(migration_id)

        if record and migration and record.get("checksum"):
            if record["checksum"].lower() != migration.checksum():
                state = CONFLICTING
                evidence = "Recorded checksum differs from the current migration source."
        elif record and migration and state == VERIFIED_APPLIED:
            evidence += " Legacy record has no checksum; source identity is unverified."

        if record and state == VERIFIED_NOT_APPLIED:
            state = CONFLICTING
            evidence += " Ledger says applied, but required postconditions are absent."
        elif record and state == UNKNOWN:
            evidence += " A ledger record exists but does not prove completion."
        results.append({
            "migration_id": migration_id,
            "state": state,
            "ledger_recorded": record is not None,
            "ledger_status": record.get("status") if record else None,
            "evidence": evidence,
        })
    return results
