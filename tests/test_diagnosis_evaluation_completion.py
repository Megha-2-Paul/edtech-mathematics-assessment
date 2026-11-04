from types import SimpleNamespace

from exam_platform import diagnosis


def _diagnose(monkeypatch, questions, responses):
    monkeypatch.setattr(diagnosis, "_error_rows", lambda _attempt_id: [])
    monkeypatch.setattr(diagnosis, "_previous_attempts", lambda *_args: [])
    monkeypatch.setattr(diagnosis, "_previous_error_counts", lambda *_args: {})

    attempt = SimpleNamespace(
        attempt_id="ATTEMPT-1",
        student_id="STUDENT-1",
        percentage=0,
    )
    return diagnosis.diagnose_attempt(attempt, None, questions, responses)


def _question(question_id):
    return SimpleNamespace(
        question_id=question_id, marks=2,
        chapter="Algebra", topic="Equations",
    )


def _response(question_id, marks_awarded):
    return SimpleNamespace(
        question_id=question_id,
        marks_awarded=marks_awarded,
        answer_status="unanswered",
        is_correct=False,
    )


def test_missing_response_is_not_counted_as_evaluated(monkeypatch):
    result = _diagnose(
        monkeypatch, [_question("Q1"), _question("Q2")],
        [_response("Q1", 0)],
    )
    assert result["evaluated_responses"] == 1
    assert result["evaluation_complete"] is False


def test_response_without_marks_is_not_counted_as_evaluated(monkeypatch):
    result = _diagnose(monkeypatch, [_question("Q1")], [_response("Q1", None)])
    assert result["evaluated_responses"] == 0
    assert result["evaluation_complete"] is False


def test_evaluated_unanswered_response_with_zero_marks_counts_as_evaluated(monkeypatch):
    result = _diagnose(monkeypatch, [_question("Q1")], [_response("Q1", 0)])
    assert result["evaluated_responses"] == 1
    assert result["evaluation_complete"] is True


def test_evaluation_is_complete_when_every_question_has_marks(monkeypatch):
    result = _diagnose(
        monkeypatch, [_question("Q1"), _question("Q2")],
        [_response("Q1", 0), _response("Q2", 2)],
    )
    assert result["evaluated_responses"] == 2
    assert result["evaluation_complete"] is True
