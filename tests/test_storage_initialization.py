import os
import subprocess
import sys
from pathlib import Path

import pytest

import exam_platform.storage as storage_module


def test_storage_constructor_does_not_initialize_database_or_load_cache(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        storage_module,
        "initialize_database",
        lambda: calls.append("database"),
    )
    monkeypatch.setattr(
        storage_module.MySQLStorage,
        "_load_cache",
        lambda self: calls.append("cache"),
    )

    storage = storage_module.MySQLStorage()

    assert calls == []
    assert storage._initialized is False


def test_storage_initialize_runs_once(monkeypatch):
    calls = []

    monkeypatch.setattr(
        storage_module,
        "initialize_database",
        lambda: calls.append("database"),
    )
    monkeypatch.setattr(
        storage_module.MySQLStorage,
        "_load_cache",
        lambda self: calls.append("cache"),
    )

    storage = storage_module.MySQLStorage()
    storage.initialize()
    storage.initialize()

    assert calls == ["database", "cache"]
    assert storage._initialized is True


def test_application_initialization_is_not_called_at_module_import():
    app_path = (
        Path(__file__).resolve().parents[1]
        / "exam_platform"
        / "app.py"
    )
    source = app_path.read_text(encoding="utf-8")

    assert "def initialize_app():" in source
    assert "    legacy_storage.initialize()" in source
    assert "    load_mock_data()" in source
    assert not __import__("re").search(
        r"(?m)^initialize_app\(\)$",
        source,
    )


def test_wsgi_entry_point_initializes_application():
    wsgi_path = Path(__file__).resolve().parents[1] / "wsgi.py"
    source = wsgi_path.read_text(encoding="utf-8")

    assert "from exam_platform.app import app, initialize_app" in source
    assert "initialize_app()" in source


def test_importing_application_does_not_open_database_connection():
    repo_root = Path(__file__).resolve().parents[1]
    script = """
from unittest.mock import patch
from sqlalchemy.engine import Engine

with patch.object(
    Engine,
    "connect",
    side_effect=AssertionError("database connection attempted during import"),
) as connect:
    import exam_platform.app

assert connect.call_count == 0
"""
    test_env = os.environ.copy()
    test_env["DATABASE_URL"] = (
        "mysql+pymysql://test:test@127.0.0.1:1/import_isolation_test"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=test_env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, (
        "Application import failed or attempted a database connection.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_load_cache_does_not_publish_partial_data_on_failure(monkeypatch):
    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def mappings(self):
            return self._rows

    class FakeConnection:
        def __init__(self):
            self.query_count = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, statement):
            self.query_count += 1

            if self.query_count == 1:
                return FakeResult([
                    {
                        "test_id": "test-1",
                        "title": "Test",
                        "subject": "Mathematics",
                        "class_level": "10",
                        "duration_minutes": 30,
                        "total_marks": 10,
                        "questions_json": "[]",
                        "status": "published",
                        "board": "CBSE",
                        "test_date": None,
                        "test_type": "practice",
                    }
                ])

            raise RuntimeError("simulated cache query failure")

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(storage_module, "engine", FakeEngine())
    monkeypatch.setattr(
        storage_module,
        "Test",
        lambda *args: object(),
    )

    storage = storage_module.MySQLStorage()

    with pytest.raises(RuntimeError, match="simulated cache query failure"):
        storage._load_cache()

    assert storage.tests == {}
    assert storage.questions == {}
    assert storage.students == {}
    assert storage.attempts == {}
    assert storage.responses == {}
    assert storage.images == {}


def test_storage_initialization_clears_partial_state_and_can_retry(monkeypatch):
    calls = []

    def load_cache(storage):
        calls.append("cache")

        if len(calls) == 1:
            storage.tests["partial"] = object()
            raise RuntimeError("simulated cache load failure")

        storage.tests["loaded"] = object()

    monkeypatch.setattr(storage_module, "initialize_database", lambda: None)
    monkeypatch.setattr(
        storage_module.MySQLStorage,
        "_load_cache",
        load_cache,
    )

    storage = storage_module.MySQLStorage()

    with pytest.raises(RuntimeError, match="simulated cache load failure"):
        storage.initialize()

    assert storage._initialized is False
    assert storage.tests == {}
    assert storage.questions == {}
    assert storage.students == {}
    assert storage.attempts == {}
    assert storage.responses == {}
    assert storage.images == {}

    storage.initialize()

    assert calls == ["cache", "cache"]
    assert storage._initialized is True
    assert set(storage.tests) == {"loaded"}
