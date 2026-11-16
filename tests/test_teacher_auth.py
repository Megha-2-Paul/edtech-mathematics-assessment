import pytest
from flask import Flask

from exam_platform.teacher_auth import register_teacher_auth


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("TEACHER_ACCESS_PASSWORD", raising=False)
    monkeypatch.delenv("TEACHER_ACCESS_USERNAME", raising=False)

    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.get("/teacher/probe")
    def teacher_probe():
        return "teacher route"

    @app.get("/teacher")
    def teacher_root():
        return "teacher root"

    @app.get("/teacherish")
    def similarly_named_route():
        return "not a teacher route"

    @app.get("/public")
    def public_route():
        return "public route"

    register_teacher_auth(app)
    return app.test_client()


def test_local_teacher_route_allows_request_without_password(auth_client):
    response = auth_client.get("/teacher/probe")
    assert response.status_code == 200


def test_render_teacher_route_returns_503_without_password(
    auth_client, monkeypatch
):
    monkeypatch.setenv("RENDER", "true")

    response = auth_client.get("/teacher/probe")

    assert response.status_code == 503
    assert response.get_data(as_text=True) == "Teacher access is not configured."


def test_teacher_route_rejects_missing_credentials(auth_client, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get("/teacher/probe")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Basic realm="Improvia Teacher"'


def test_teacher_route_rejects_invalid_credentials(auth_client, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get(
        "/teacher/probe",
        headers={"Authorization": "Basic dGVhY2hlcjp3cm9uZw=="},
    )

    assert response.status_code == 401


def test_teacher_route_accepts_valid_credentials(auth_client, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get(
        "/teacher/probe",
        auth=("teacher", "test-secret"),
    )

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "teacher route"


def test_custom_teacher_username_is_respected(auth_client, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_USERNAME", "admin-user")
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get(
        "/teacher/probe",
        auth=("admin-user", "test-secret"),
    )

    assert response.status_code == 200


@pytest.mark.parametrize("path", ["/public", "/teacherish"])
def test_non_teacher_routes_are_not_protected(
    auth_client, monkeypatch, path
):
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get(path)

    assert response.status_code == 200


def test_teacher_root_route_requires_authentication(auth_client, monkeypatch):
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = auth_client.get("/teacher")

    assert response.status_code == 401