import pytest
from pymysql.err import (
    OperationalError as MySQLOperationalError,
    ProgrammingError as MySQLProgrammingError,
)
from sqlalchemy.exc import OperationalError, ProgrammingError

import exam_platform.storage as storage_module


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=None):
        self.statements.append(str(statement))
        outcome = next(self.outcomes)

        if isinstance(outcome, BaseException):
            raise outcome

        return outcome


def _install_connection(monkeypatch, outcomes):
    connection = FakeConnection(outcomes)
    monkeypatch.setattr(
        storage_module.engine,
        "connect",
        lambda: connection,
    )
    return connection


def _mysql_programming_error(code):
    driver_error = MySQLProgrammingError(
        code,
        "Simulated MySQL programming error",
    )
    return ProgrammingError("SELECT ...", {}, driver_error)


def _mysql_operational_error(code):
    driver_error = MySQLOperationalError(
        code,
        "Simulated MySQL operational error",
    )
    return OperationalError("SELECT ...", {}, driver_error)


CASES = [
    pytest.param(
        "get_chapters",
        lambda storage: storage.get_chapters(
            "CBSE", 10, "Mathematics"
        ),
        "curriculum_chapters",
        "FROM chapters",
        [{"chapter_id": 1, "chapter_name": "Algebra"}],
        [{"chapter_id": 1, "chapter_name": "Algebra"}],
        id="chapters",
    ),
    pytest.param(
        "get_subjects",
        lambda storage: storage.get_subjects(),
        "subject_catalog",
        "FROM subjects",
        [
            {
                "subject_id": 1,
                "subject_name": "Mathematics",
                "subject_code": "041",
                "active": 1,
            }
        ],
        [
            {
                "subject_id": 1,
                "name": "Mathematics",
                "subject_code": "041",
                "active": 1,
            }
        ],
        id="subjects",
    ),
]


@pytest.mark.parametrize(
    "method_name,invoke,new_marker,legacy_marker,new_rows,expected_new",
    CASES,
)
def test_new_schema_query_returns_results_without_legacy_fallback(
    monkeypatch,
    method_name,
    invoke,
    new_marker,
    legacy_marker,
    new_rows,
    expected_new,
):
    connection = _install_connection(
        monkeypatch,
        [FakeResult(new_rows)],
    )

    result = invoke(storage_module.MySQLStorage())

    assert result == expected_new
    assert len(connection.statements) == 1
    assert new_marker in connection.statements[0]
    assert legacy_marker not in connection.statements[0]


@pytest.mark.parametrize(
    "method_name,invoke,new_marker,legacy_marker,new_rows,expected_new",
    CASES,
)
def test_missing_new_schema_table_uses_legacy_fallback(
    monkeypatch,
    method_name,
    invoke,
    new_marker,
    legacy_marker,
    new_rows,
    expected_new,
):
    legacy_rows = [{"legacy_id": 99, "name": "Legacy record"}]
    connection = _install_connection(
        monkeypatch,
        [
            _mysql_programming_error(1146),
            FakeResult(legacy_rows),
        ],
    )

    result = invoke(storage_module.MySQLStorage())

    assert result == legacy_rows
    assert len(connection.statements) == 2
    assert new_marker in connection.statements[0]
    assert legacy_marker in connection.statements[1]


@pytest.mark.parametrize(
    "method_name,invoke,new_marker,legacy_marker,new_rows,expected_new",
    CASES,
)
def test_empty_new_schema_result_uses_legacy_fallback(
    monkeypatch,
    method_name,
    invoke,
    new_marker,
    legacy_marker,
    new_rows,
    expected_new,
):
    legacy_rows = [{"legacy_id": 99, "name": "Legacy record"}]
    connection = _install_connection(
        monkeypatch,
        [
            FakeResult([]),
            FakeResult(legacy_rows),
        ],
    )

    result = invoke(storage_module.MySQLStorage())

    assert result == legacy_rows
    assert len(connection.statements) == 2
    assert new_marker in connection.statements[0]
    assert legacy_marker in connection.statements[1]


@pytest.mark.parametrize(
    "method_name,invoke,new_marker,legacy_marker,new_rows,expected_new",
    CASES,
)
def test_unrelated_programming_error_is_propagated(
    monkeypatch,
    method_name,
    invoke,
    new_marker,
    legacy_marker,
    new_rows,
    expected_new,
):
    connection = _install_connection(
        monkeypatch,
        [_mysql_programming_error(1064)],
    )

    with pytest.raises(ProgrammingError):
        invoke(storage_module.MySQLStorage())

    assert len(connection.statements) == 1
    assert new_marker in connection.statements[0]


@pytest.mark.parametrize(
    "method_name,invoke,new_marker,legacy_marker,new_rows,expected_new",
    CASES,
)
def test_database_operational_error_is_propagated(
    monkeypatch,
    method_name,
    invoke,
    new_marker,
    legacy_marker,
    new_rows,
    expected_new,
):
    connection = _install_connection(
        monkeypatch,
        [_mysql_operational_error(2003)],
    )

    with pytest.raises(OperationalError):
        invoke(storage_module.MySQLStorage())

    assert len(connection.statements) == 1
    assert new_marker in connection.statements[0]
