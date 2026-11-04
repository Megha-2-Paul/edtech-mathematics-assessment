"""Route-level regression tests for AI JSON uploads."""

import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask

from exam_platform.teacher_csrf import register_teacher_csrf
from question_bank.extraction import review_app

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "exam_platform" / "templates"
UPLOAD_URL = "/teacher/extraction-review/json-upload"
CSRF_TOKEN = "json-upload-test-token"


def _client():
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    app.secret_key = "json-upload-test-only-secret"
    app.config["TESTING"] = True

    @app.get("/tests")
    def test_listing():
        return ""

    @app.get(
        "/teacher/extraction-review/",
        endpoint="extraction_review.dashboard",
    )
    def dashboard():
        return ""

    app.add_url_rule(
        UPLOAD_URL,
        endpoint="extraction_review.json_upload",
        view_func=review_app._json_upload_view,
        methods=["GET", "POST"],
    )

    register_teacher_csrf(app)
    return app.test_client()


def _post_upload(client, payload, filename="sample.json"):
    with client.session_transaction() as session:
        session["_teacher_csrf_token"] = CSRF_TOKEN

    return client.post(
        UPLOAD_URL,
        data={
            "teacher_csrf_token": CSRF_TOKEN,
            "json_file": (BytesIO(payload), filename),
        },
        content_type="multipart/form-data",
    )


def test_malformed_json_shows_general_guidance_without_running_importer(monkeypatch):
    client = _client()
    importer = Mock()
    monkeypatch.setattr(review_app, "AIJSONBulkImporter", importer)

    response = _post_upload(
        client,
        br'{"questions":[{"question_text":"\sqrt{x}"}]}',
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Invalid JSON in sample.json" in body
    assert "line" in body
    assert "column" in body
    assert "Check the JSON syntax" in body
    assert "backslashes" in body.lower()
    importer.assert_not_called()


def test_invalid_utf8_shows_encoding_error_without_running_importer(monkeypatch):
    client = _client()
    importer = Mock()
    monkeypatch.setattr(review_app, "AIJSONBulkImporter", importer)

    response = _post_upload(client, b"\xff\xfe")

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "sample.json is not valid UTF-8 JSON" in body
    importer.assert_not_called()


def test_valid_json_upload_is_saved_to_isolated_inbox(tmp_path, monkeypatch):
    client = _client()
    payload = {
        "questions": [
            {"question_text": "What is 2 + 2?", "question_type": "saq"}
        ]
    }

    result = SimpleNamespace(
        total=1,
        review_required=1,
        duplicates=0,
        validation_pending=0,
        invalid=0,
    )

    class StubImporter:
        def __init__(self, existing_questions):
            assert list(existing_questions) == []

        def prepare(self, submitted_payload):
            assert submitted_payload == payload
            return result

    save_batch = Mock()

    monkeypatch.setattr(review_app, "AIJSONBulkImporter", StubImporter)
    monkeypatch.setattr(review_app, "stable_batch_id", lambda value: "batch-test")
    monkeypatch.setattr(review_app, "_persistent_save_batch", save_batch)
    monkeypatch.setattr(review_app._legacy, "INBOX_DIR", tmp_path)
    monkeypatch.setattr(
        review_app._legacy,
        "storage",
        SimpleNamespace(questions={}),
    )

    response = _post_upload(
        client,
        json.dumps(payload).encode("utf-8"),
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "is ready for human review" in body

    saved_files = list(tmp_path.glob("*.json"))
    assert len(saved_files) == 1
    assert json.loads(saved_files[0].read_text(encoding="utf-8")) == payload

    save_batch.assert_called_once()
    assert save_batch.call_args.kwargs["batch_id"] == "batch-test"
    assert save_batch.call_args.kwargs["payload"] == payload
