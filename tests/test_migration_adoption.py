from sqlalchemy import create_engine, inspect, text

from question_bank.migrations.adoption import (
    CONFLICTING,
    UNKNOWN,
    VERIFIED_NOT_APPLIED,
    inspect_legacy_migrations,
)


def test_adoption_inspection_is_read_only_and_reports_absent_migration():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE students (student_id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE question_assets (asset_id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE questions (question_id TEXT PRIMARY KEY)"))
    before = set(inspect(engine).get_table_names())

    results = inspect_legacy_migrations(engine, ("001_question_bank_foundation",))
    after = set(inspect(engine).get_table_names())

    assert results[0]["state"] == VERIFIED_NOT_APPLIED
    assert before == after
    engine.dispose()


def test_adoption_does_not_claim_curriculum_data_migration_from_ddl_alone():
    engine = create_engine("sqlite://")
    tables = (
        "subject_catalog", "curriculum_catalog", "curriculum_units",
        "canonical_concepts", "curriculum_chapters",
        "question_curriculum_map", "student_subject_enrollments",
    )
    with engine.begin() as connection:
        for table in tables:
            connection.execute(text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY)"))
    result = inspect_legacy_migrations(engine, ("005_curriculum_question_reuse",))[0]
    assert result["state"] == UNKNOWN
    engine.dispose()


def test_ledger_conflict_is_reported_when_schema_postcondition_is_absent():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("""
            INSERT INTO schema_migrations(migration_id)
            VALUES ('001_question_bank_foundation')
        """))
        connection.execute(text("CREATE TABLE questions (question_id TEXT PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE question_assets (asset_id TEXT PRIMARY KEY)"))
    result = inspect_legacy_migrations(engine, ("001_question_bank_foundation",))[0]
    assert result["state"] == CONFLICTING
    assert result["ledger_recorded"] is True
    engine.dispose()


def test_mismatched_recorded_checksum_is_conflicting():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id TEXT PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                checksum CHAR(64)
            )
        """))
        connection.execute(text("""
            INSERT INTO schema_migrations(migration_id, checksum)
            VALUES ('001_question_bank_foundation', :checksum)
        """), {"checksum": "0" * 64})
    result = inspect_legacy_migrations(engine, ("001_question_bank_foundation",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()
