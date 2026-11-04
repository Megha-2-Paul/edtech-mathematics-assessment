from pathlib import Path

from flask import Flask, jsonify

from exam_platform.teacher_csrf import register_teacher_csrf


ROOT = Path(__file__).resolve().parents[1]


def _client():
    app = Flask(__name__)
    app.secret_key = "csrf-test-only-secret"
    register_teacher_csrf(app)

    @app.route("/teacher/mutate", methods=["GET", "POST"])
    def mutate():
        return jsonify({"ok": True})

    @app.route("/api/registrations/google-form", methods=["POST"])
    def registration_webhook():
        return jsonify({"ok": True})

    @app.route("/extraction-review/item/review", methods=["POST"], endpoint="extraction_review.review")
    def extraction_review_mutation():
        return jsonify({"ok": True})

    return app.test_client()


def test_teacher_mutation_rejects_missing_and_invalid_csrf_tokens():
    client = _client()
    missing = client.post("/teacher/mutate")
    assert missing.status_code == 400
    assert missing.get_json() == {"error": "Invalid or missing CSRF token"}

    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = "expected-token"

    invalid = client.post("/teacher/mutate", data={"teacher_csrf_token": "wrong-token"})
    assert invalid.status_code == 400


def test_teacher_mutation_accepts_a_valid_form_token():
    client = _client()
    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = "expected-token"
    response = client.post("/teacher/mutate", data={"teacher_csrf_token": "expected-token"})
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_teacher_mutation_accepts_a_valid_header_token():
    client = _client()
    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = "expected-token"
    response = client.post("/teacher/mutate", headers={"X-Teacher-CSRF-Token": "expected-token"})
    assert response.status_code == 200


def test_get_requests_and_registration_webhook_are_not_blocked():
    client = _client()
    assert client.get("/teacher/mutate").status_code == 200
    assert client.post("/api/registrations/google-form").status_code == 200


def test_access_link_path_has_no_special_csrf_exemption():
    client = _client()
    response = client.post("/teacher/students/STU1/access-link", json={"ok": True})
    assert response.status_code == 400


def test_extraction_review_mutation_requires_csrf_token():
    client = _client()
    assert client.post("/extraction-review/item/review").status_code == 400
    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = "expected-token"
    response = client.post(
        "/extraction-review/item/review",
        data={"teacher_csrf_token": "expected-token"},
    )
    assert response.status_code == 200


def test_teacher_post_forms_include_csrf_tokens():
    template_paths = [
        ROOT / "exam_platform/templates/teacher_evaluation.html",
        ROOT / "exam_platform/templates/teacher_question_form.html",
        ROOT / "exam_platform/templates/teacher_test_form.html",
        ROOT / "exam_platform/templates/teacher_questions.html",
        ROOT / "exam_platform/templates/extraction_json_upload.html",
        ROOT / "exam_platform/templates/extraction_review_item.html",
    ]
    for path in template_paths:
        assert 'name="teacher_csrf_token"' in path.read_text(encoding="utf-8"), path.name
