import exam_platform.eligibility as eligibility
from sqlalchemy.exc import SQLAlchemyError
from exam_platform.models import Student, Test as Assessment


def student(subject="Mathematics", class_level=12, board="CBSE"):
    return Student(
        student_id="STU001",
        name="Test Student",
        email="student@example.com",
        class_level=class_level,
        board=board,
        subject=subject,
    )


def matching_test():
    return Assessment(
        "T1", "CBSE XII Mathematics", "Mathematics",
        12, 60, 80, board="CBSE"
    )


class FakeResult:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None, error=None):
        self.row = row
        self.error = error
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, params):
        self.statements.append((str(statement), params))
        if self.error:
            raise self.error
        return FakeResult(self.row)


def mock_enrollment_query(monkeypatch, row=None, error=None):
    connection = FakeConnection(row=row, error=error)
    monkeypatch.setattr(
        eligibility.engine,
        "connect",
        lambda: connection,
    )
    return connection


def test_mathematics_student_can_access_matching_test(monkeypatch):
    mock_enrollment_query(monkeypatch, row=(1,))
    assert eligibility.is_test_eligible(student(), matching_test())


def test_student_without_active_enrollment_is_not_eligible(monkeypatch):
    mock_enrollment_query(monkeypatch, row=None)
    assert not eligibility.is_test_eligible(student(), matching_test())


def test_database_error_fails_closed(monkeypatch):
    mock_enrollment_query(
        monkeypatch,
        error=SQLAlchemyError("database unavailable"),
    )
    assert not eligibility.is_test_eligible(student(), matching_test())


def test_applied_mathematics_student_cannot_access_mathematics_test(monkeypatch):
    mock_enrollment_query(monkeypatch, row=None)
    assert not eligibility.is_test_eligible(
        student(subject="Applied Mathematics"),
        matching_test(),
    )


def test_mathematics_student_cannot_access_applied_mathematics_test(monkeypatch):
    applied_test = Assessment(
        "T2", "CBSE XII Applied Mathematics",
        "Applied Mathematics", 12, 60, 80, board="CBSE"
    )
    mock_enrollment_query(monkeypatch, row=None)
    assert not eligibility.is_test_eligible(student(), applied_test)


def test_board_and_class_are_part_of_eligibility(monkeypatch):
    mock_enrollment_query(monkeypatch, row=(1,))
    assert not eligibility.is_test_eligible(
        student(class_level=11), matching_test()
    )
    assert not eligibility.is_test_eligible(
        student(board="ICSE"), matching_test()
    )


def test_inactive_student_is_not_eligible(monkeypatch):
    inactive_student = student()
    inactive_student.status = "inactive"

    connection = mock_enrollment_query(monkeypatch, row=(1,))
    assert not eligibility.is_test_eligible(
        inactive_student, matching_test()
    )
    assert connection.statements == []


def test_unregistered_student_is_not_eligible(monkeypatch):
    guest = Student("STU002", "Guest Student", "", subject=None)
    connection = mock_enrollment_query(monkeypatch, row=(1,))

    assert not eligibility.is_test_eligible(guest, matching_test())
    assert eligibility.registration_required(guest)
    assert connection.statements == []


def test_registration_required_when_enrollment_is_missing(monkeypatch):
    mock_enrollment_query(monkeypatch, row=None)
    assert eligibility.registration_required(student())


def test_registration_not_required_when_enrollment_exists(monkeypatch):
    mock_enrollment_query(monkeypatch, row=(1,))
    assert not eligibility.registration_required(student())


def test_registration_required_when_database_check_fails(monkeypatch):
    mock_enrollment_query(
        monkeypatch,
        error=SQLAlchemyError("database unavailable"),
    )
    assert eligibility.registration_required(student())
