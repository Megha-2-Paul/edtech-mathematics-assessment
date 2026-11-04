import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "question_bank" / "migrations" / "006_exam_monitoring_mode.py"
)
SPEC = importlib.util.spec_from_file_location(
    "exam_monitoring_mode_migration", MIGRATION_PATH
)
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def test_dry_run_does_not_add_missing_column():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text(
                "CREATE TABLE tests (test_id TEXT PRIMARY KEY, status TEXT)"
            ))
        plan = migration.inspect_migration(engine)
        assert plan == {
            "column_exists": False,
            "invalid_rows": None,
            "needs_schema_repair": False,
        }
        columns = {column["name"] for column in inspect(engine).get_columns("tests")}
        assert "monitoring_mode" not in columns
    finally:
        engine.dispose()


def test_apply_adds_monitoring_column_with_off_default():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text(
                "CREATE TABLE tests (test_id TEXT PRIMARY KEY, status TEXT)"
            ))
            db.execute(text(
                "INSERT INTO tests (test_id, status) VALUES ('T1', 'active')"
            ))
        result = migration.apply_migration(engine)
        assert result["column_added"] is True
        with engine.connect() as db:
            value = db.execute(text(
                "SELECT monitoring_mode FROM tests WHERE test_id='T1'"
            )).scalar_one()
        assert value == "off"
    finally:
        engine.dispose()


def test_apply_normalizes_invalid_values_and_preserves_valid_modes():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text(
                "CREATE TABLE tests (test_id TEXT PRIMARY KEY, monitoring_mode VARCHAR(20) NOT NULL DEFAULT 'off')"
            ))
            db.execute(text(
                "INSERT INTO tests (test_id, monitoring_mode) VALUES "
                "('T1', 'invalid'), ('T2', 'optional'), "
                "('T4', 'required')"
            ))
        result = migration.apply_migration(engine)
        assert result["column_added"] is False
        with engine.connect() as db:
            values = db.execute(text(
                "SELECT test_id, monitoring_mode FROM tests ORDER BY test_id"
            )).all()
        assert values == [
            ("T1", "off"), ("T2", "optional"),
            ("T4", "required"),
        ]
    finally:
        engine.dispose()


def test_migration_fails_if_tests_table_is_missing():
    engine = create_engine("sqlite://")
    try:
        with pytest.raises(RuntimeError, match="tests table does not exist"):
            migration.inspect_migration(engine)
    finally:
        engine.dispose()




def test_migration_rejects_incompatible_existing_column():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text(
                "CREATE TABLE tests "
                "(test_id TEXT PRIMARY KEY, monitoring_mode TEXT)"
            ))

        with pytest.raises(RuntimeError, match="Incompatible"):
            migration.inspect_migration(engine)

    finally:
        engine.dispose()



def test_unsupported_schema_repair_fails_before_data_changes():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as db:
            db.execute(text(
                "CREATE TABLE tests "
                "(test_id TEXT PRIMARY KEY, monitoring_mode VARCHAR(20) NULL)"
            ))
            db.execute(text(
                "INSERT INTO tests (test_id, monitoring_mode) "
                "VALUES ('T1', NULL)"
            ))

        with pytest.raises(RuntimeError, match="No data changes were made"):
            migration.apply_migration(engine)

        with engine.connect() as db:
            value = db.execute(text(
                "SELECT monitoring_mode FROM tests WHERE test_id='T1'"
            )).scalar_one_or_none()

        assert value is None

    finally:
        engine.dispose()
