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
