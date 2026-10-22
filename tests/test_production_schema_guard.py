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
        SimpleNamespace(begin=lambda: pytest.fail("Production startup must not open a write transaction")),
    )

    database.initialize_database()

    assert calls == ["validated"]


def test_render_never_seeds_demo_data_or_enables_retake_mode(monkeypatch):
    from exam_platform import mock_data

    original = mock_data.storage.get_student_test_attempt
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("LOAD_DEMO_DATA", "1")
    monkeypatch.setenv("TESTING_MODE", "1")
    monkeypatch.setattr(
        mock_data.storage,
        "create_question",
        lambda *_: pytest.fail("Demo questions must never be inserted on Render"),
    )
    monkeypatch.setattr(
        mock_data.storage,
        "create_test",
        lambda *_: pytest.fail("Demo tests must never be inserted on Render"),
    )

    mock_data.load_mock_data()
    assert mock_data.storage.get_student_test_attempt == original
