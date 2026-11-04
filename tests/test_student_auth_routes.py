import importlib
from contextlib import nullcontext

import pytest

from exam_platform.models import Student

app_module = importlib.import_module("exam_platform.app")


class FakeResult:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class FakeConnection:
    def __init__(self, login_row):
        self.login_row = login_row
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "SELECT c.password_hash" in sql:
            return FakeResult(self.login_row)

        return FakeResult()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(app_module.app.config, "TESTING", True)
    return app_module.app.test_client()


def _active_student():
    return Student(
        student_id="STU-001",
        name="Test Student",
        email="student@example.com",
        status="active",
    )


def _set_shared_csrf_session(client, student_id=None):
    with client.session_transaction() as session:
        session["_csrf_token"] = "shared-test-token"
        if student_id:
            session["student_id"] = student_id


def _set_both_csrf_tokens(client):
    with client.session_transaction() as session:
        session["_csrf_token"] = "shared-test-token"
        session["_student_csrf_token"] = "student-test-token"


def _install_login_database(monkeypatch, login_row):
    connection = FakeConnection(login_row)
    monkeypatch.setattr(
        app_module.engine,
        "begin",
        lambda: nullcontext(connection),
    )
    return connection


def test_anonymous_student_page_redirects_to_login(client):
    response = client.get("/tests")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/login")


def test_anonymous_assessment_api_returns_401_after_csrf_validation(client):
    _set_both_csrf_tokens(client)

    response = client.post(
        "/api/test/TEST-001/start",
        headers={
            "X-CSRF-Token": "shared-test-token",
            "X-Student-CSRF-Token": "student-test-token",
        },
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Student login required"}


def test_active_student_can_access_test_listing(client, monkeypatch):
    monkeypatch.setattr(
        app_module.storage,
        "get_student",
        lambda student_id: _active_student(),
    )
    monkeypatch.setattr(
        app_module.storage,
        "get_all_tests",
        list,
    )

    _set_shared_csrf_session(client, "STU-001")

    response = client.get("/tests")

    assert response.status_code == 200


def test_inactive_student_is_denied_and_session_is_cleared(client, monkeypatch):
    inactive_student = _active_student()
    inactive_student.status = "inactive"

    monkeypatch.setattr(
        app_module.storage,
        "get_student",
        lambda student_id: inactive_student,
    )

    _set_shared_csrf_session(client, "STU-001")

    response = client.get("/tests")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/login")

    with client.session_transaction() as session:
        assert "student_id" not in session


def test_unknown_student_is_denied_and_session_is_cleared(client, monkeypatch):
    monkeypatch.setattr(
        app_module.storage,
        "get_student",
        lambda student_id: None,
    )

    _set_shared_csrf_session(client, "UNKNOWN")

    response = client.get("/tests")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/login")

    with client.session_transaction() as session:
        assert "student_id" not in session


def test_valid_login_establishes_student_session(client, monkeypatch):
    connection = _install_login_database(
        monkeypatch,
        {
            "password_hash": "stored-password-hash",
            "failed_login_count": 0,
            "locked_until": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        app_module,
        "check_password_hash",
        lambda stored_hash, password: password == "correct-password",
    )

    login_page = client.get("/student/login")
    assert login_page.status_code == 200

    with client.session_transaction() as session:
        csrf_token = session["_csrf_token"]

    response = client.post(
        "/student/login",
        data={
            "csrf_token": csrf_token,
            "student_id": "stu-001",
            "password": "correct-password",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tests")

    with client.session_transaction() as session:
        assert session["student_id"] == "STU-001"
        assert session.permanent is True

    assert any("UPDATE student_access_credentials" in sql for sql, _ in connection.statements)


def test_invalid_login_does_not_establish_student_session(client, monkeypatch):
    connection = _install_login_database(
        monkeypatch,
        {
            "password_hash": "stored-password-hash",
            "failed_login_count": 0,
            "locked_until": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        app_module,
        "check_password_hash",
        lambda stored_hash, password: False,
    )

    login_page = client.get("/student/login")
    assert login_page.status_code == 200

    with client.session_transaction() as session:
        csrf_token = session["_csrf_token"]

    response = client.post(
        "/student/login",
        data={
            "csrf_token": csrf_token,
            "student_id": "STU-001",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401

    with client.session_transaction() as session:
        assert "student_id" not in session

    assert any("UPDATE student_access_credentials" in sql for sql, _ in connection.statements)


def test_logout_clears_student_session(client):
    _set_shared_csrf_session(client, "STU-001")

    response = client.post(
        "/student/logout",
        data={"csrf_token": "shared-test-token"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/login")

    with client.session_transaction() as session:
        assert "student_id" not in session


def test_logout_rejects_missing_csrf_token_and_preserves_session(client):
    _set_shared_csrf_session(client, "STU-001")

    response = client.post("/student/logout")

    assert response.status_code == 400

    with client.session_transaction() as session:
        assert session["student_id"] == "STU-001"


class FakeActivationConnection:
    def __init__(self, token_row, student_row=None):
        self.token_row = token_row
        self.student_row = student_row
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "SELECT student_id,expires_at,used_at" in sql:
            return FakeResult(self.token_row)

        if "SELECT status FROM students" in sql:
            return FakeResult(self.student_row)

        return FakeResult()


def _activation_token_row(expired=False, used=False):
    from datetime import datetime, timedelta

    now = datetime.now()

    return {
        "student_id": "STU-001",
        "expires_at": now - timedelta(hours=1) if expired else now + timedelta(hours=1),
        "used_at": now if used else None,
    }


def _install_activation_database(monkeypatch, token_row, student_row=None):
    connection = FakeActivationConnection(token_row, student_row)

    monkeypatch.setattr(
        app_module.engine,
        "begin",
        lambda: nullcontext(connection),
    )

    return connection


def _set_activation_csrf(client):
    with client.session_transaction() as session:
        session["_csrf_token"] = "activation-test-token"


def test_valid_activation_establishes_student_session(client, monkeypatch):
    connection = _install_activation_database(
        monkeypatch,
        _activation_token_row(),
        {"status": "active"},
    )
    _set_activation_csrf(client)

    response = client.post(
        "/student/activate",
        data={
            "token": "valid-activation-token",
            "csrf_token": "activation-test-token",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tests")

    with client.session_transaction() as session:
        assert session["student_id"] == "STU-001"
        assert session.permanent is True

    insert_statement = next(
        (params for sql, params in connection.statements
         if "INSERT INTO student_access_credentials" in sql),
        None,
    )
    assert insert_statement is not None
    assert insert_statement["password_hash"] != "StrongPassword123!"
    assert any(
        "UPDATE student_access_tokens" in sql
        for sql, _ in connection.statements
    )


@pytest.mark.parametrize(
    ("expired", "used"),
    [
        (True, False),
        (False, True),
    ],
    ids=["expired-token", "already-used-token"],
)
def test_expired_or_used_activation_token_is_rejected(
    client, monkeypatch, expired, used
):
    connection = _install_activation_database(
        monkeypatch,
        _activation_token_row(expired=expired, used=used),
        {"status": "active"},
    )
    _set_activation_csrf(client)

    response = client.post(
        "/student/activate",
        data={
            "token": "invalid-activation-token",
            "csrf_token": "activation-test-token",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )

    assert response.status_code == 400
    assert not any(
        "INSERT INTO student_access_credentials" in sql
        for sql, _ in connection.statements
    )
    assert not any(
        "UPDATE student_access_tokens" in sql
        for sql, _ in connection.statements
    )

    with client.session_transaction() as session:
        assert "student_id" not in session


def test_inactive_student_cannot_activate_account(client, monkeypatch):
    connection = _install_activation_database(
        monkeypatch,
        _activation_token_row(),
        {"status": "inactive"},
    )
    _set_activation_csrf(client)

    response = client.post(
        "/student/activate",
        data={
            "token": "valid-activation-token",
            "csrf_token": "activation-test-token",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )

    assert response.status_code == 400
    assert not any(
        "INSERT INTO student_access_credentials" in sql
        for sql, _ in connection.statements
    )
    assert not any(
        "UPDATE student_access_tokens" in sql
        for sql, _ in connection.statements
    )

    with client.session_transaction() as session:
        assert "student_id" not in session


@pytest.mark.parametrize(
    ("password", "confirmation", "expected_message"),
    [
        ("Short123!", "Short123!", "at least 12 characters"),
        ("StrongPassword123!", "DifferentPassword123!", "do not match"),
    ],
    ids=["short-password", "password-mismatch"],
)
def test_activation_rejects_invalid_passwords(
    client, monkeypatch, password, confirmation, expected_message
):
    def unexpected_database_access():
        raise AssertionError("Database should not be accessed")

    monkeypatch.setattr(
        app_module.engine,
        "begin",
        unexpected_database_access,
    )
    _set_activation_csrf(client)

    response = client.post(
        "/student/activate",
        data={
            "token": "valid-activation-token",
            "csrf_token": "activation-test-token",
            "password": password,
            "confirm_password": confirmation,
        },
    )

    assert response.status_code == 400
    assert expected_message.encode() in response.data


def test_activation_rejects_missing_csrf_token(client, monkeypatch):
    def unexpected_database_access():
        raise AssertionError("Database should not be accessed")

    monkeypatch.setattr(
        app_module.engine,
        "begin",
        unexpected_database_access,
    )

    response = client.post(
        "/student/activate",
        data={
            "token": "valid-activation-token",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid or missing CSRF token"
    }

