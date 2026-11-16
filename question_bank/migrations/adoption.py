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


def _verify(engine, migration_id: str) -> tuple[str, str]:
    inspector = inspect(engine)

    if migration_id == "001_question_bank_foundation":
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
        has_indexes = required_indexes.issubset(_index_names(inspector, "questions"))
        has_indexes = has_indexes and "idx_question_asset_page" in _index_names(
            inspector, "question_assets"
        )
        if present == total and has_columns and has_indexes:
            return VERIFIED_APPLIED, "Foundation tables, provenance columns, and indexes are present."
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
        with engine.connect() as connection:
            missing = connection.execute(text(
                "SELECT COUNT(*) FROM questions "
                "WHERE canonical_question_id IS NULL OR canonical_question_id = ''"
            )).scalar_one()
        if missing:
            return PARTIALLY_APPLIED, "Some questions still lack canonical_question_id."
        return VERIFIED_APPLIED, "Solution table exists and all question IDs are canonicalized."

    if migration_id == "003_canonical_math_taxonomy":
        required = {"canonical_subjects", "canonical_chapters", "syllabus_units", "syllabus_chapters"}
        present, total = _table_state(inspector, required)
        if present == total:
            return UNKNOWN, "Taxonomy tables exist; taxonomy seed/data postconditions need source-level verification."
        if present == 0:
            return VERIFIED_NOT_APPLIED, "Legacy taxonomy tables are absent."
        return PARTIALLY_APPLIED, "Only some legacy taxonomy tables are present."

    if migration_id == "004_student_registration_subject":
        columns = _columns(inspector, "students")
        indexes = _index_names(inspector, "students")
        if "subject" in columns and "idx_students_eligibility" in indexes:
            return VERIFIED_APPLIED, "Student subject column and eligibility index are present."
        if "subject" not in columns and "idx_students_eligibility" not in indexes:
            return VERIFIED_NOT_APPLIED, "Student subject column and eligibility index are absent."
        return PARTIALLY_APPLIED, "Only part of the registration schema is present."

    if migration_id == "005_curriculum_question_reuse":
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
        columns = {
            c["name"]: c
            for c in inspector.get_columns("tests")
        } if inspector.has_table("tests") else {}
        column = columns.get("monitoring_mode")
        if column is None:
            return VERIFIED_NOT_APPLIED, "tests.monitoring_mode is absent."
        with engine.connect() as connection:
            invalid = connection.execute(text(
                "SELECT COUNT(*) FROM tests WHERE monitoring_mode IS NULL "
                "OR monitoring_mode NOT IN ('off', 'optional', 'required')"
            )).scalar_one()
        if invalid:
            return PARTIALLY_APPLIED, "monitoring_mode exists but contains invalid or null values."
        return VERIFIED_APPLIED, "monitoring_mode exists and all values are valid."

    if migration_id == "008_migration_ledger_upgrade":
        columns = _columns(inspector, "schema_migrations")
        expected = {
            "migration_id", "applied_at", "status", "checksum", "started_at",
            "completed_at", "error_summary", "execution_version",
        }
        if expected.issubset(columns):
            return VERIFIED_APPLIED, "All migration ledger columns are present."
        if not columns:
            return VERIFIED_NOT_APPLIED, "Migration ledger is absent."
        if {"migration_id", "applied_at"}.issubset(columns):
            return PARTIALLY_APPLIED, "Legacy ledger exists but extension is incomplete."
        return CONFLICTING, "Migration ledger has an incompatible structure."

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
