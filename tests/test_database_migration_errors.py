import pytest
from pymysql.err import (
    OperationalError as MySQLOperationalError,
    ProgrammingError as MySQLProgrammingError,
)
from sqlalchemy.exc import OperationalError, ProgrammingError

import database as database_module


class FakeResult:
    def scalar_one_or_none(self):
        return None


class FakeConnection:
    def __init__(self, failure_fragment=None, error=None):
        self.failure_fragment = failure_fragment
        self.error = error
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)

        if (
            self.failure_fragment is not None
            and self.failure_fragment in sql
        ):
            raise self.error

        return FakeResult()


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection

    def begin(self):
        return self.connection


def _programming_error(code):
    original = MySQLProgrammingError(
        code,
        "Simulated MySQL programming error",
    )
    return ProgrammingError("ALTER TABLE ...", {}, original)


def _operational_error(code):
    original = MySQLOperationalError(
        code,
        "Simulated MySQL operational error",
    )
    return OperationalError("ALTER TABLE ...", {}, original)


def _run_with_fake_engine(monkeypatch, failure_fragment=None, error=None):
    connection = FakeConnection(failure_fragment, error)
    monkeypatch.setattr(
        database_module,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.delenv("RENDER", raising=False)

    database_module.initialize_database()
    return connection


ADD_COLUMN_STATEMENTS = [
    "ALTER TABLE questions ADD COLUMN status",
    "ALTER TABLE questions ADD COLUMN source_type",
    "ALTER TABLE questions ADD COLUMN verification_status",
    "ALTER TABLE questions ADD COLUMN canonical_question_id",
    "ALTER TABLE students ADD COLUMN subject",
]


@pytest.mark.parametrize("statement", ADD_COLUMN_STATEMENTS)
def test_duplicate_column_error_is_ignored_for_add_column(
    monkeypatch,
    statement,
):
    connection = _run_with_fake_engine(
        monkeypatch,
        statement,
        _programming_error(1060),
    )

    assert any(statement in sql for sql in connection.statements)


def test_unrelated_programming_error_propagates_for_add_column(monkeypatch):
    connection = FakeConnection(
        "ALTER TABLE questions ADD COLUMN status",
        _programming_error(1064),
    )
    monkeypatch.setattr(
        database_module,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.delenv("RENDER", raising=False)

    with pytest.raises(ProgrammingError):
        database_module.initialize_database()

    assert len(connection.statements) == len(database_module.SCHEMA) + 1


def test_operational_error_propagates_for_add_column(monkeypatch):
    connection = FakeConnection(
        "ALTER TABLE questions ADD COLUMN status",
        _operational_error(2003),
    )
    monkeypatch.setattr(
        database_module,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.delenv("RENDER", raising=False)

    with pytest.raises(OperationalError):
        database_module.initialize_database()

    assert len(connection.statements) == len(database_module.SCHEMA) + 1


@pytest.mark.parametrize("error_code", [1068, 1064])
def test_email_column_modification_errors_are_not_suppressed(
    monkeypatch,
    error_code,
):
    connection = FakeConnection(
        "ALTER TABLE students MODIFY COLUMN email",
        _programming_error(error_code),
    )
    monkeypatch.setattr(
        database_module,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.delenv("RENDER", raising=False)

    with pytest.raises(ProgrammingError):
        database_module.initialize_database()

    assert any(
        "ALTER TABLE students MODIFY COLUMN email" in sql
        for sql in connection.statements
    )
    assert not any(
        "UPDATE students SET email=NULL" in sql
        for sql in connection.statements
    )


def test_email_update_errors_are_not_suppressed(monkeypatch):
    connection = FakeConnection(
        "UPDATE students SET email=NULL",
        _programming_error(1064),
    )
    monkeypatch.setattr(
        database_module,
        "engine",
        FakeEngine(connection),
    )
    monkeypatch.delenv("RENDER", raising=False)

    with pytest.raises(ProgrammingError):
        database_module.initialize_database()

    assert any(
        "ALTER TABLE students MODIFY COLUMN email" in sql
        for sql in connection.statements
    )
    assert any(
        "UPDATE students SET email=NULL" in sql
        for sql in connection.statements
    )
