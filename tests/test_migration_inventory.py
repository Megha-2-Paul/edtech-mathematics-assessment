"""Static consistency checks for the documented database migration inventory."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "database" / "MIGRATION_INVENTORY.md"
MIGRATIONS = ROOT / "question_bank" / "migrations"

EXPECTED_SCRIPTS = {
    "001_question_bank_foundation.sql",
    "002_canonical_question_ingestion.sql",
    "003_canonical_math_taxonomy.py",
    "004_student_registration_subject.sql",
    "005_curriculum_question_reuse.py",
    "005_curriculum_question_reuse_audit.py",
    "006_exam_monitoring_mode.py",
    "007_student_access.py",
    "008_migration_ledger_upgrade.py",
}


def test_migration_inventory_exists_and_lists_every_script():
    assert INVENTORY.is_file()
    document = INVENTORY.read_text(encoding="utf-8")

    discovered = {
        path.name
        for path in MIGRATIONS.iterdir()
        if path.is_file()
        and path.name[:3].isdigit()
        and path.name[3:4] == "_"
        and path.suffix in {".py", ".sql"}
    }
    assert discovered == EXPECTED_SCRIPTS

    for filename in EXPECTED_SCRIPTS:
        assert f"`{filename}`" in document


def test_inventory_distinguishes_apply_migrations_from_read_only_audit():
    document = INVENTORY.read_text(encoding="utf-8")

    assert "`005_curriculum_question_reuse.py`" in document
    assert "`005_curriculum_question_reuse_audit.py`" in document
    assert "read-only audit/helper scripts" in document
    assert "schema **and data** migration" in document


def test_inventory_records_runtime_required_curriculum_dependencies():
    document = INVENTORY.read_text(encoding="utf-8")

    assert "`exam_platform/eligibility.py`" in document
    assert "`student_subject_enrollments`" in document
    assert "`subject_catalog`" in document
    assert "**Core runtime required**" in document


def test_inventory_preserves_mysql_client_execution_constraint():
    document = INVENTORY.read_text(encoding="utf-8")

    assert "`DELIMITER`" in document
    assert "MySQL-client script" in document
    assert "Not safe to split naively into ordinary SQLAlchemy statements" in document


def test_inventory_explicitly_excludes_database_operations():
    document = INVENTORY.read_text(encoding="utf-8")

    assert "does not:" in document
    assert "connect to local, Aiven or production databases" in document
    assert "apply, fake, stamp, rollback or reorder migrations" in document
