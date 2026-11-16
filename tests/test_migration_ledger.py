from datetime import datetime

import pytest
from sqlalchemy import create_engine, text

from question_bank.migrations.ledger import read_ledger, record_migration
from question_bank.migrations.manifest import MIGRATIONS, validate_manifest

import importlib.util
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "question_bank"
    / "migrations"
    / "008_migration_ledger_upgrade.py"
)
SPEC = importlib.util.spec_from_file_location("migration_ledger_upgrade", MIGRATION_PATH)
UPGRADE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPGRADE)
upgrade_ledger = UPGRADE.upgrade_ledger


def test_upgrade_preserves_legacy_rows_and_old_insert_contract():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        connection.execute(
            text("INSERT INTO schema_migrations(migration_id) VALUES ('001_existing')")
        )

    before = read_ledger(engine)[0]["applied_at"]
    added = upgrade_ledger(engine)

    assert set(added) == {
        "status", "checksum", "started_at", "completed_at",
        "error_summary", "execution_version",
    }
    legacy = read_ledger(engine)[0]
    assert legacy["migration_id"] == "001_existing"
    assert legacy["applied_at"] == before
    assert legacy["status"] == "applied"
    assert legacy["checksum"] is None

    # The unchanged INSERT used by migrations 001 and 002 remains valid.
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO schema_migrations(migration_id) VALUES ('002_existing')")
        )
    assert {row["migration_id"] for row in read_ledger(engine)} == {
        "001_existing", "002_existing"
    }
    engine.dispose()


def test_upgrade_is_idempotent():
    engine = create_engine("sqlite://")
    first = upgrade_ledger(engine)
    second = upgrade_ledger(engine)
    assert len(first) == 6
    assert second == []
    engine.dispose()


def test_upgrade_adds_only_missing_columns():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE schema_migrations (
                migration_id VARCHAR(100) PRIMARY KEY,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) NOT NULL DEFAULT 'applied'
            )
        """))
    added = upgrade_ledger(engine)
    assert set(added) == {
        "checksum", "started_at", "completed_at", "error_summary",
        "execution_version",
    }
    engine.dispose()


def test_upgrade_fails_closed_for_incompatible_ledger():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE schema_migrations (wrong_id TEXT)"))
    with pytest.raises(RuntimeError, match="Incompatible"):
        upgrade_ledger(engine)
    columns = {c["name"] for c in __import__("sqlalchemy").inspect(engine).get_columns("schema_migrations")}
    assert columns == {"wrong_id"}
    engine.dispose()


def test_record_migration_validates_status_and_checksum():
    engine = create_engine("sqlite://")
    upgrade_ledger(engine)
    with pytest.raises(ValueError, match="Unsupported"):
        record_migration(engine, "test_migration", "complete")
    with pytest.raises(ValueError, match="checksum"):
        record_migration(engine, "test_migration", "applied", checksum="bad")
    record_migration(
        engine, "test_migration", "applied",
        checksum="a" * 64, execution_version="1",
    )
    row = next(r for r in read_ledger(engine) if r["migration_id"] == "test_migration")
    assert row["status"] == "applied"
    assert row["checksum"] == "a" * 64
    engine.dispose()


def test_manifest_is_complete_and_checksums_are_sha256():
    validate_manifest()
    assert {m.migration_id for m in MIGRATIONS} == {
        "001_question_bank_foundation",
        "002_canonical_question_ingestion",
        "003_canonical_math_taxonomy",
        "004_student_registration_subject",
        "005_curriculum_question_reuse",
        "006_exam_monitoring_mode",
        "008_migration_ledger_upgrade",
    }
    assert all(len(m.checksum()) == 64 for m in MIGRATIONS)
