from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask, session

from exam_platform import evaluation
from exam_platform.teacher_csrf import register_teacher_csrf


@pytest.fixture
def route_setup(monkeypatch):
    app = Flask(__name__)
    app.secret_key = "evaluation-route-test-secret"
    register_teacher_csrf(app)
    app.register_blueprint(evaluation.evaluation_bp)

    attempt = SimpleNamespace(
        attempt_id="ATTEMPT-1",
        test_id="TEST-1",
        student_id="STUDENT-1",
        submitted_at=None,
        started_at=None,
        score=0,
        percentage=0,
        attempt_rate=0,
        accuracy=0,
    )

    question1 = SimpleNamespace(
        question_id="Q1",
        question_type="short_answer",
        marks=5,
        correct_answer=None,
        handwritten_upload_mode=False,
    )
    question2 = SimpleNamespace(
        question_id="Q2",
        question_type="short_answer",
        marks=5,
        correct_answer=None,
        handwritten_upload_mode=False,
    )

    response1 = SimpleNamespace(
        response_id="R1",
        question_id="Q1",
        selected_answer=None,
        marks_awarded=0,
        is_correct=False,
        answer_status="answered",
    )
    response2 = SimpleNamespace(
        response_id="R2",
        question_id="Q2",
        selected_answer=None,
        marks_awarded=0,
        is_correct=False,
        answer_status="answered",
    )

    test = SimpleNamespace(
        test_id="TEST-1",
        questions=["Q1", "Q2"],
    )

    monkeypatch.setattr(
        evaluation, "_attempt_or_404", lambda attempt_id: attempt
    )
    monkeypatch.setattr(evaluation.storage, "get_test", lambda test_id: test)
    monkeypatch.setattr(
        evaluation.storage, "get_questions", lambda ids: [question1, question2]
    )
    monkeypatch.setattr(
        evaluation.storage,
        "get_attempt_responses",
        lambda attempt_id: [response1, response2],
    )

    save_mock = Mock()
    monkeypatch.setattr(
        evaluation, "_save_response_evaluation", save_mock
    )
    monkeypatch.setattr(
        evaluation, "_evaluate_attempt", lambda attempt_id: attempt
    )
    monkeypatch.setattr(evaluation.storage, "update_attempt", Mock())
    monkeypatch.setattr(evaluation, "_update_question_history", Mock())

    client = app.test_client()

    with client.session_transaction() as sess:
        sess["_teacher_csrf_token"] = "test-csrf-token"

    return SimpleNamespace(
        client=client,
        save_mock=save_mock,
        attempt=attempt,
        questions=[question1, question2],
        responses=[response1, response2],
    )


def _post_marks(client, first_mark, second_mark):
    return client.post(
        "/teacher/evaluate/ATTEMPT-1",
        data={
            "teacher_csrf_token": "test-csrf-token",
            "marks_Q1": first_mark,
            "marks_Q2": second_mark,
        },
        follow_redirects=False,
    )


@pytest.mark.parametrize(
    ("first_mark", "second_mark"),
    [
        ("-0.5", "2"),
        ("5.5", "2"),
        ("", "2"),
        ("0.25", "2"),
        ("NaN", "2"),
        ("2", "Infinity"),
    ],
)
def test_invalid_marks_prevent_all_evaluation_saves(
    route_setup, first_mark, second_mark
):
    response = _post_marks(
        route_setup.client, first_mark, second_mark
    )

    assert response.status_code == 302
    route_setup.save_mock.assert_not_called()


def test_valid_marks_are_passed_to_evaluation_saver(route_setup):
    response = _post_marks(route_setup.client, "2.5", "5")

    assert response.status_code == 302
    assert route_setup.save_mock.call_count == 2
    assert route_setup.save_mock.call_args_list[0].args[2] == 2.5
    assert route_setup.save_mock.call_args_list[1].args[2] == 5.0


def test_invalid_csrf_token_prevents_evaluation(route_setup):
    response = route_setup.client.post(
        "/teacher/evaluate/ATTEMPT-1",
        data={
            "teacher_csrf_token": "wrong-token",
            "marks_Q1": "2.5",
            "marks_Q2": "5",
        },
    )

    assert response.status_code == 400
    route_setup.save_mock.assert_not_called()
