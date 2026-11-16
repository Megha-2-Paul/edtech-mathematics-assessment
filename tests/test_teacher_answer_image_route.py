from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from exam_platform import evaluation
from exam_platform.teacher_auth import register_teacher_auth


@pytest.fixture
def image_route_setup(monkeypatch, tmp_path):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("TEACHER_ACCESS_PASSWORD", raising=False)
    monkeypatch.delenv("TEACHER_ACCESS_USERNAME", raising=False)

    app = Flask(__name__)
    app.secret_key = "teacher-image-route-test-secret"
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app.register_blueprint(evaluation.evaluation_bp)
    register_teacher_auth(app)

    attempt = SimpleNamespace(
        attempt_id="ATTEMPT-1",
        test_id="TEST-1",
    )
    test = SimpleNamespace(
        test_id="TEST-1",
        questions=["Q1"],
    )
    question = SimpleNamespace(
        question_id="Q1",
        handwritten_upload_mode=True,
    )
    image = SimpleNamespace(
        image_id="IMAGE-1",
        attempt_id="ATTEMPT-1",
        file_path=str(tmp_path / "answer.png"),
        page_number=1,
        original_filename="answer.png",
    )

    monkeypatch.setattr(
        evaluation, "_attempt_or_404", lambda _attempt_id: attempt
    )
    monkeypatch.setattr(
        evaluation.storage, "get_test", lambda _test_id: test
    )
    monkeypatch.setattr(
        evaluation.storage, "get_questions", lambda _ids: [question]
    )
    monkeypatch.setattr(
        evaluation.storage,
        "get_attempt_images",
        lambda _attempt_id, _question_id: [image],
    )

    read_mock = Mock(return_value=(b"image-bytes", "image/png"))
    monkeypatch.setattr(
        evaluation.media, "read_stored_image", read_mock
    )

    return SimpleNamespace(
        client=app.test_client(),
        image=image,
        read_mock=read_mock,
        upload_folder=str(tmp_path),
    )


def test_teacher_image_route_serves_verified_private_image(image_route_setup):
    setup = image_route_setup

    response = setup.client.get(
        "/teacher/attempt/ATTEMPT-1/images/IMAGE-1/content"
    )

    assert response.status_code == 200
    assert response.data == b"image-bytes"
    assert response.mimetype == "image/png"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    setup.read_mock.assert_called_once_with(
        setup.image.file_path,
        upload_folder=setup.upload_folder,
    )


def test_teacher_image_route_rejects_image_from_another_attempt(
    image_route_setup,
):
    setup = image_route_setup
    setup.image.attempt_id = "OTHER-ATTEMPT"

    response = setup.client.get(
        "/teacher/attempt/ATTEMPT-1/images/IMAGE-1/content"
    )

    assert response.status_code == 404
    setup.read_mock.assert_not_called()


def test_teacher_image_route_rejects_unknown_image_id(image_route_setup):
    setup = image_route_setup

    response = setup.client.get(
        "/teacher/attempt/ATTEMPT-1/images/UNKNOWN/content"
    )

    assert response.status_code == 404
    setup.read_mock.assert_not_called()


def test_teacher_evaluation_generates_private_image_route_url(
    image_route_setup, monkeypatch,
):
    setup = image_route_setup

    monkeypatch.setattr(
        evaluation.storage,
        "get_attempt_responses",
        lambda _attempt_id: [],
    )
    monkeypatch.setattr(
        evaluation,
        "render_template",
        lambda _template, **context: (
            context["response_data"][0]["images"][0]["url"]
        ),
    )

    response = setup.client.get("/teacher/evaluate/ATTEMPT-1")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == (
        "/teacher/attempt/ATTEMPT-1/images/IMAGE-1/content"
    )

def test_teacher_image_route_rejects_unauthenticated_request(
    image_route_setup, monkeypatch
):
    setup = image_route_setup
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = setup.client.get(
        "/teacher/attempt/ATTEMPT-1/images/IMAGE-1/content"
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == 'Basic realm="Improvia Teacher"'
    setup.read_mock.assert_not_called()


def test_teacher_image_route_accepts_authenticated_request(
    image_route_setup, monkeypatch
):
    setup = image_route_setup
    monkeypatch.setenv("TEACHER_ACCESS_PASSWORD", "test-secret")

    response = setup.client.get(
        "/teacher/attempt/ATTEMPT-1/images/IMAGE-1/content",
        auth=("teacher", "test-secret"),
    )

    assert response.status_code == 200
    assert response.data == b"image-bytes"
    setup.read_mock.assert_called_once()