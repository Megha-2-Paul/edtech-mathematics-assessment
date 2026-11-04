import pytest
from flask import Flask, jsonify, render_template_string

from exam_platform.student_csrf import register_student_csrf
from exam_platform.teacher_csrf import register_teacher_csrf


TOKEN = "student-test-token"

STUDENT_ENDPOINTS = {
    "start_test": "/api/test/TEST1/start",
    "save_response": "/api/attempt/ATTEMPT1/response",
    "upload_answer_image": "/api/attempt/ATTEMPT1/upload",
    "delete_image": "/api/attempt/ATTEMPT1/delete-image/IMAGE1",
    "submit_attempt": "/api/attempt/ATTEMPT1/submit",
}


@pytest.fixture
def client():
    app = Flask(__name__)
    app.secret_key = "csrf-test-only-secret"

    register_teacher_csrf(app)
    register_student_csrf(app)

    for endpoint, path in STUDENT_ENDPOINTS.items():
        app.add_url_rule(
            path,
            endpoint=endpoint,
            view_func=lambda: jsonify({"ok": True}),
            methods=["POST", "DELETE"],
        )

    @app.route("/token")
    def token_page():
        return render_template_string(
            '<meta name="student-csrf-token" content="{{ student_csrf_token }}">'
        )

    @app.route("/api/registrations/google-form", methods=["POST"])
    def registration_webhook():
        return jsonify({"ok": True})

    @app.route("/teacher/mutate", methods=["POST"])
    def teacher_mutation():
        return jsonify({"ok": True})

    @app.route("/read-only", methods=["GET"])
    def read_only():
        return jsonify({"ok": True})

    return app.test_client()


@pytest.mark.parametrize(
    ("endpoint", "path"),
    STUDENT_ENDPOINTS.items(),
)
def test_student_mutations_reject_missing_tokens(client, endpoint, path):
    method = "delete" if endpoint == "delete_image" else "post"

    response = getattr(client, method)(path)

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid or missing CSRF token"
    }


@pytest.mark.parametrize(
    ("endpoint", "path"),
    STUDENT_ENDPOINTS.items(),
)
def test_student_mutations_reject_invalid_tokens(client, endpoint, path):
    with client.session_transaction() as session:
        session["_student_csrf_token"] = TOKEN

    method = "delete" if endpoint == "delete_image" else "post"

    response = getattr(client, method)(
        path,
        headers={"X-Student-CSRF-Token": "wrong-token"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("endpoint", "path"),
    STUDENT_ENDPOINTS.items(),
)
def test_student_mutations_accept_valid_header_tokens(client, endpoint, path):
    with client.session_transaction() as session:
        session["_student_csrf_token"] = TOKEN

    method = "delete" if endpoint == "delete_image" else "post"

    response = getattr(client, method)(
        path,
        headers={"X-Student-CSRF-Token": TOKEN},
    )

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_student_mutation_accepts_valid_form_token(client):
    with client.session_transaction() as session:
        session["_student_csrf_token"] = TOKEN

    response = client.post(
        STUDENT_ENDPOINTS["start_test"],
        data={"student_csrf_token": TOKEN},
    )

    assert response.status_code == 200


def test_student_csrf_token_is_injected_into_templates(client):
    response = client.get("/token")

    assert response.status_code == 200
    assert b'student-csrf-token' in response.data

    with client.session_transaction() as session:
        assert session.get("_student_csrf_token")


def test_get_requests_are_not_blocked(client):
    response = client.get("/read-only")

    assert response.status_code == 200


def test_google_registration_webhook_is_not_blocked(client):
    response = client.post("/api/registrations/google-form")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_teacher_csrf_protection_remains_active(client):
    response = client.post("/teacher/mutate")

    assert response.status_code == 400

    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = "teacher-test-token"

    response = client.post(
        "/teacher/mutate",
        headers={"X-Teacher-CSRF-Token": "teacher-test-token"},
    )

    assert response.status_code == 200