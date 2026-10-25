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
