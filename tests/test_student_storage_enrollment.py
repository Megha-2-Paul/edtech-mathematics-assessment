import pytest
from sqlalchemy.exc import SQLAlchemyError

import exam_platform.storage as storage_module
from exam_platform.models import Student


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeConnection:
    def __init__(self, existing_student=None, enrollment_error=None):
        self.existing_student = existing_student
        self.enrollment_error = enrollment_error
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "SELECT student_id FROM students" in sql:
            return FakeResult(self.existing_student)

        if "INSERT INTO student_subject_enrollments" in sql:
            if self.enrollment_error:
                raise self.enrollment_error

        return FakeResult()


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True
        return False


def make_storage():
    storage = storage_module.MySQLStorage.__new__(
        storage_module.MySQLStorage
    )
    storage.students = {}
    return storage


def make_student(**overrides):
    values = {
        "student_id": "STU100",
        "name": "Test Student",
        "email": " student@example.com ",
        "class_level": 10,
        "board": "CBSE",
        "subject": "Mathematics",
    }
    values.update(overrides)
    return Student(**values)


def install_fake_transaction(monkeypatch, connection):
    transaction = FakeTransaction(connection)
    begin_calls = []

    def fake_begin():
        begin_calls.append(transaction)
        return transaction

    monkeypatch.setattr(storage_module.engine, "begin", fake_begin)
    return transaction, begin_calls


def test_student_and_enrollment_are_saved_in_one_transaction(monkeypatch):
    storage = make_storage()
    connection = FakeConnection()
    transaction, begin_calls = install_fake_transaction(
        monkeypatch, connection
    )
    student = make_student()

    storage.create_student(student)

    sql_statements = [sql for sql, _ in connection.statements]

    assert len(begin_calls) == 1
    assert any("INSERT INTO students" in sql for sql in sql_statements)
    assert any(
        "INSERT INTO student_subject_enrollments" in sql
        for sql in sql_statements
    )
    assert transaction.committed
    assert not transaction.rolled_back
    assert storage.students[student.student_id] is student
    assert student.email == "student@example.com"


def test_enrollment_failure_rolls_back_and_does_not_update_cache(monkeypatch):
    storage = make_storage()
    connection = FakeConnection(
        enrollment_error=SQLAlchemyError("enrollment write failed")
    )
    transaction, _ = install_fake_transaction(monkeypatch, connection)
    student = make_student()

    with pytest.raises(SQLAlchemyError):
        storage.create_student(student)

    assert transaction.rolled_back
    assert not transaction.committed
    assert student.student_id not in storage.students


def test_guest_student_is_saved_without_subject_enrollment(monkeypatch):
    storage = make_storage()
    connection = FakeConnection()
    transaction, _ = install_fake_transaction(monkeypatch, connection)
    guest = make_student(
        email="",
        class_level=None,
        board=None,
        subject=None,
    )

    storage.create_student(guest)

    sql_statements = [sql for sql, _ in connection.statements]

    assert any("INSERT INTO students" in sql for sql in sql_statements)
    assert not any(
        "INSERT INTO student_subject_enrollments" in sql
        for sql in sql_statements
    )
    assert transaction.committed
    assert storage.students[guest.student_id] is guest
    assert guest.email is None


def test_register_student_rejects_unsupported_subject_before_database_call(
    monkeypatch,
):
    storage = make_storage()
    begin_calls = []

    def unexpected_begin():
        begin_calls.append(True)
        raise AssertionError("Database transaction should not start")

    monkeypatch.setattr(storage_module.engine, "begin", unexpected_begin)

    student = make_student(subject="Unsupported Subject")

    with pytest.raises(ValueError, match="supported board/class/subject"):
        storage.register_student(student)

    assert begin_calls == []
    assert student.student_id not in storage.students


def test_existing_student_is_updated_with_enrollment_in_same_transaction(
    monkeypatch,
):
    storage = make_storage()
    connection = FakeConnection(existing_student="STU100")
    transaction, begin_calls = install_fake_transaction(
        monkeypatch, connection
    )
    student = make_student()

    storage.create_student(student)

    sql_statements = [sql for sql, _ in connection.statements]

    assert len(begin_calls) == 1
    assert any("UPDATE students" in sql for sql in sql_statements)
    assert any(
        "INSERT INTO student_subject_enrollments" in sql
        for sql in sql_statements
    )
    assert transaction.committed
    assert storage.students[student.student_id] is student