from types import SimpleNamespace

import pytest


def test_render_startup_only_validates_schema(monkeypatch):
    import database

    calls = []
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(
        database,
        "_validate_production_schema",
        lambda: calls.append("validated"),
    )
    monkeypatch.setattr(
        database,
        "engine",
        SimpleNamespace(
            begin=lambda: pytest.fail(
                "Production startup must not open a write transaction"
            )
        ),
    )

    database.initialize_database()

    assert calls == ["validated"]


def test_production_schema_guard_fails_when_required_tables_are_missing(monkeypatch):
    import database

    class FakeInspector:
        def get_table_names(self):
            return ["students"]

        def get_columns(self, table):
            return [
                {"name": name}
                for name in ("student_id", "name", "email", "status")
            ]

    monkeypatch.setattr(database, "inspect", lambda _engine: FakeInspector())

    with pytest.raises(RuntimeError, match="No automatic DDL or data repair"):
        database._validate_production_schema()

def test_render_mock_data_guard_precedes_demo_data_loading():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "exam_platform"
        / "mock_data.py"
    ).read_text(encoding="utf-8")
    start = source.index("def load_mock_data()")
    end = source.index("\n    questions = [", start)
    loader = source[start:end]

    assert 'if os.getenv("RENDER"):' in loader
    assert loader.index('if os.getenv("RENDER"):') < loader.index(
        'if os.getenv("LOAD_DEMO_DATA", "0") != "1":'
    )


def test_production_schema_guard_requires_monitoring_mode(monkeypatch):
    import database

    class FakeInspector:
        def get_table_names(self):
            return [
                statement.split("CREATE TABLE IF NOT EXISTS ", 1)[1].split(" ", 1)[0]
                for statement in database.SCHEMA
            ] + ["student_access_credentials", "student_access_tokens"]

        def get_columns(self, table):
            required_columns = {
                "students": {"student_id", "name", "email", "status"},
                "tests": {
                    "test_id", "title", "duration_minutes",
                    "total_marks", "questions_json",
                },
                "questions": {
                    "question_id", "question_content_json",
                    "answer_choices_json", "marks",
                },
                "attempts": {
                    "attempt_id", "student_id", "test_id",
                    "started_at", "status",
                },
                "responses": {
                    "response_id", "attempt_id", "question_id",
                    "answer_status",
                },
                "answer_images": {
                    "image_id", "attempt_id", "question_id", "file_path",
                },
                "student_access_credentials": {
                    "student_id", "password_hash", "failed_login_count",
                    "locked_until", "last_login_at", "created_at", "updated_at",
                },
                "student_access_tokens": {
                    "token_hash", "student_id", "expires_at", "used_at",
                    "created_at",
                },
            }
            return [{"name": name} for name in required_columns.get(table, set())]

    monkeypatch.setattr(database, "inspect", lambda _engine: FakeInspector())

    with pytest.raises(RuntimeError, match="monitoring_mode"):
        database._validate_production_schema()


def test_application_does_not_use_a_hard_coded_production_session_secret():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "exam_platform"
        / "app.py"
    ).read_text(encoding="utf-8")

    assert "dev-secret-key-change-in-production" not in source
    assert 'os.getenv("SECRET_KEY")' in source
    assert 'SESSION_COOKIE_HTTPONLY=True' in source
    assert 'SESSION_COOKIE_SAMESITE="Lax"' in source
    assert 'SESSION_COOKIE_SECURE=bool(os.getenv("RENDER"))' in source

def _schema_guard_inspector(database, missing_table=None, missing_column=None):
    required_columns = {
        "students": {"student_id", "name", "email", "status"},
        "tests": {
            "test_id", "title", "duration_minutes", "total_marks",
            "questions_json", "monitoring_mode",
        },
        "questions": {
            "question_id", "question_content_json",
            "answer_choices_json", "marks",
        },
        "attempts": {
            "attempt_id", "student_id", "test_id", "started_at", "status",
        },
        "responses": {
            "response_id", "attempt_id", "question_id", "answer_status",
        },
        "answer_images": {
            "image_id", "attempt_id", "question_id", "file_path",
        },
        "student_access_credentials": {
            "student_id", "password_hash", "failed_login_count",
            "locked_until", "last_login_at", "created_at", "updated_at",
        },
        "student_access_tokens": {
            "token_hash", "student_id", "expires_at", "used_at", "created_at",
        },
    }

    class FakeInspector:
        def get_table_names(self):
            tables = [
                statement.split("CREATE TABLE IF NOT EXISTS ", 1)[1].split(" ", 1)[0]
                for statement in database.SCHEMA
            ]
            tables.extend([
                "student_access_credentials",
                "student_access_tokens",
            ])
            if missing_table:
                tables.remove(missing_table)
            return tables

        def get_columns(self, table):
            columns = set(required_columns.get(table, set()))
            if missing_column and missing_column[0] == table:
                columns.discard(missing_column[1])
            return [{"name": name} for name in columns]

    return FakeInspector()


def test_production_schema_guard_requires_student_access_tables(monkeypatch):
    import database

    inspector = _schema_guard_inspector(
        database,
        missing_table="student_access_credentials",
    )
    monkeypatch.setattr(database, "inspect", lambda _engine: inspector)

    with pytest.raises(RuntimeError, match="student_access_credentials"):
        database._validate_production_schema()


def test_production_schema_guard_requires_student_access_columns(monkeypatch):
    import database

    inspector = _schema_guard_inspector(
        database,
        missing_column=("student_access_tokens", "token_hash"),
    )
    monkeypatch.setattr(database, "inspect", lambda _engine: inspector)

    with pytest.raises(RuntimeError, match="token_hash"):
        database._validate_production_schema()
