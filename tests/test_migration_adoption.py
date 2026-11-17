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



def test_adoption_rejects_foundation_index_with_wrong_columns():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE questions (question_id TEXT PRIMARY KEY, source_type VARCHAR(20) NOT NULL DEFAULT 'MANUAL', verification_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED', canonical_question_id VARCHAR(40))"))
        connection.execute(text("CREATE TABLE question_assets (asset_id TEXT PRIMARY KEY, question_id TEXT, page_number INTEGER, bbox_json TEXT, asset_role VARCHAR(50), source_asset_id VARCHAR(70))"))
        connection.execute(text("CREATE INDEX idx_questions_source_type ON questions (verification_status)"))
        connection.execute(text("CREATE INDEX idx_questions_verification_status ON questions (verification_status)"))
        connection.execute(text("CREATE INDEX idx_questions_canonical ON questions (canonical_question_id)"))
        connection.execute(text("CREATE INDEX idx_question_asset_page ON question_assets (question_id, page_number)"))
        for table in (
            "source_papers", "question_occurrences", "question_groups",
            "question_parts", "question_extraction_runs",
            "question_extraction_results", "question_verifications",
            "extraction_jobs", "extraction_providers", "extraction_feedback",
        ):
            connection.execute(text(f"CREATE TABLE {table} (id TEXT PRIMARY KEY)"))

    result = inspect_legacy_migrations(engine, ("001_question_bank_foundation",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()


def test_adoption_rejects_registration_index_with_wrong_columns():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE students (student_id TEXT PRIMARY KEY, subject VARCHAR(100))"))
        connection.execute(text("CREATE INDEX idx_students_eligibility ON students (student_id)"))

    result = inspect_legacy_migrations(engine, ("004_student_registration_subject",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()


def test_adoption_rejects_incompatible_monitoring_mode_definition():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE tests (test_id TEXT PRIMARY KEY, "
            "monitoring_mode VARCHAR(30) NOT NULL DEFAULT 'off')"
        ))

    result = inspect_legacy_migrations(engine, ("006_exam_monitoring_mode",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()



def test_adoption_rejects_incompatible_question_solutions_schema():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE questions (question_id TEXT PRIMARY KEY, canonical_question_id TEXT)"))
        connection.execute(text("""
            CREATE TABLE question_solutions (
                question_solution_id BIGINT PRIMARY KEY,
                question_id VARCHAR(40) NOT NULL,
                solution_content TEXT,
                marking_scheme TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                verified BOOLEAN NOT NULL DEFAULT 0,
                source_type VARCHAR(30) NOT NULL DEFAULT 'extracted',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(question_id) REFERENCES questions(question_id) ON DELETE CASCADE
            )
        """))
        connection.execute(text(
            "CREATE INDEX idx_question_solution_question "
            "ON question_solutions (question_id)"
        ))
        connection.execute(text(
            "CREATE INDEX wrong_unique_index "
            "ON question_solutions (question_id, version)"
        ))

    result = inspect_legacy_migrations(engine, ("002_canonical_question_ingestion",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()


def test_adoption_rejects_incompatible_migration_ledger_definition():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(30) NOT NULL DEFAULT 'applied',
                checksum CHAR(64),
                started_at DATETIME,
                completed_at DATETIME,
                error_summary TEXT,
                execution_version VARCHAR(30)
            )
        """))

    result = inspect_legacy_migrations(engine, ("008_migration_ledger_upgrade",))[0]
    assert result["state"] == CONFLICTING
    engine.dispose()


def test_adoption_accepts_valid_registration_schema():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                status VARCHAR(20),
                board VARCHAR(30),
                class_level VARCHAR(20),
                subject VARCHAR(100)
            )
        """))
        connection.execute(text("""
            CREATE INDEX idx_students_eligibility
            ON students (status, board, class_level, subject)
        """))

    result = inspect_legacy_migrations(
        engine, ("004_student_registration_subject",)
    )[0]
    assert result["state"] == "VERIFIED_APPLIED"
    engine.dispose()


def test_adoption_accepts_valid_question_solutions_schema():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE questions (
                question_id VARCHAR(40) PRIMARY KEY,
                canonical_question_id VARCHAR(40)
            )
        """))
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(text("""
            INSERT INTO schema_migrations(migration_id)
            VALUES ('002_canonical_question_ingestion')
        """))
        connection.execute(text("""
            CREATE TABLE question_solutions (
                question_solution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id VARCHAR(40) NOT NULL,
                solution_content TEXT,
                marking_scheme TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                verified BOOLEAN NOT NULL DEFAULT 0,
                source_type VARCHAR(30) NOT NULL DEFAULT 'extracted',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (question_id, version),
                FOREIGN KEY(question_id)
                    REFERENCES questions(question_id) ON DELETE CASCADE
            )
        """))
        connection.execute(text("""
            CREATE INDEX idx_question_solution_question
            ON question_solutions (question_id)
        """))

    result = inspect_legacy_migrations(
        engine, ("002_canonical_question_ingestion",)
    )[0]
    assert result["state"] == "VERIFIED_APPLIED"
    engine.dispose()


def test_adoption_accepts_valid_migration_ledger_schema():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) NOT NULL DEFAULT 'applied',
                checksum CHAR(64),
                started_at DATETIME,
                completed_at DATETIME,
                error_summary TEXT,
                execution_version VARCHAR(30)
            )
        """))
        connection.execute(text("""
            INSERT INTO schema_migrations(migration_id)
            VALUES ('008_migration_ledger_upgrade')
        """))

    result = inspect_legacy_migrations(
        engine, ("008_migration_ledger_upgrade",)
    )[0]
    assert result["state"] == "VERIFIED_APPLIED"
    engine.dispose()

def test_schema_column_matches_requires_autoincrement():
    from question_bank.migrations.adoption import _schema_column_matches

    class Dialect:
        name = "mysql"

    class Bind:
        dialect = Dialect()

    class Inspector:
        bind = Bind()

        def has_table(self, table):
            return True

        def get_columns(self, table):
            return [{
                "name": "question_solution_id",
                "type": "BIGINT",
                "nullable": False,
                "default": None,
                "autoincrement": False,
            }]

    inspector = Inspector()

    assert not _schema_column_matches(
        inspector,
        "question_solutions",
        "question_solution_id",
        ("BIGINT",),
        False,
        autoincrement=True,
    )


def test_schema_column_matches_accepts_autoincrement():
    from question_bank.migrations.adoption import _schema_column_matches

    class Dialect:
        name = "mysql"

    class Bind:
        dialect = Dialect()

    class Inspector:
        bind = Bind()

        def has_table(self, table):
            return True

        def get_columns(self, table):
            return [{
                "name": "question_solution_id",
                "type": "BIGINT",
                "nullable": False,
                "default": None,
                "autoincrement": True,
            }]

    assert _schema_column_matches(
        Inspector(),
        "question_solutions",
        "question_solution_id",
        ("BIGINT",),
        False,
        autoincrement=True,
    )


def test_column_default_contains_requires_update_clause():
    from question_bank.migrations.adoption import _column_default_contains

    class Inspector:
        def has_table(self, table):
            return True

        def get_columns(self, table):
            return [{
                "name": "updated_at",
                "default": "CURRENT_TIMESTAMP",
            }]

    assert not _column_default_contains(
        Inspector(),
        "question_solutions",
        "updated_at",
        "ON UPDATE CURRENT_TIMESTAMP",
    )


def test_column_default_contains_accepts_update_clause():
    from question_bank.migrations.adoption import _column_default_contains

    class Inspector:
        def has_table(self, table):
            return True

        def get_columns(self, table):
            return [{
                "name": "updated_at",
                "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
            }]

    assert _column_default_contains(
        Inspector(),
        "question_solutions",
        "updated_at",
        "ON UPDATE CURRENT_TIMESTAMP",
    )
