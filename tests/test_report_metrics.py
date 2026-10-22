from types import SimpleNamespace

from collections import Counter

from exam_platform.diagnosis import (
    _attempt_metrics,
    _build_recurring_errors,
    _unique_error_rows,
)


def question(qid, marks):
    return SimpleNamespace(question_id=qid, marks=marks)


def response(qid, status, marks, correct=None):
    return SimpleNamespace(
        question_id=qid,
        answer_status=status,
        marks_awarded=marks,
        is_correct=correct,
    )


def test_attempted_work_accuracy_is_marks_based_and_unattempted_is_explicit():
    questions = [question("Q1", 4), question("Q2", 6), question("Q3", 10)]
    responses = [
        response("Q1", "answered", 2, False),
        response("Q2", "partial", 3, False),
        response("Q3", "unanswered", 0, False),
    ]

    result = _attempt_metrics(questions, responses, official_total_marks=20)

    assert result["score"] == 5
    assert result["percentage"] == 25
    assert result["attempted"] == 2
    assert result["attempt_rate"] == 66.67
    assert result["attempted_available_marks"] == 10
    assert result["attempted_marks_awarded"] == 5
    assert result["accuracy"] == 50
    assert result["unattempted"] == 1
    assert result["unattempted_available_marks"] == 10
    assert result["evaluation_complete"] is True
    assert result["report_ready"] is True


def test_missing_response_is_not_treated_as_evaluated_or_unattempted():
    questions = [question("Q1", 5), question("Q2", 5)]
    responses = [response("Q1", "answered", 4, False)]

    result = _attempt_metrics(questions, responses, official_total_marks=10)

    assert result["evaluated_responses"] == 1
    assert result["missing_response_ids"] == ["Q2"]
    assert result["evaluation_complete"] is False
    assert result["report_ready"] is False
    assert result["unattempted"] == 0


def test_null_marks_are_not_treated_as_evaluated():
    questions = [question("Q1", 5)]
    responses = [response("Q1", "answered", None, None)]

    result = _attempt_metrics(questions, responses, official_total_marks=5)

    assert result["evaluation_complete"] is False
    assert result["report_ready"] is False
    assert result["unevaluated_question_ids"] == ["Q1"]


def test_zero_denominators_return_none_not_zero():
    result = _attempt_metrics([], [], official_total_marks=0)

    assert result["percentage"] is None
    assert result["attempt_rate"] is None
    assert result["accuracy"] is None
    assert result["report_ready"] is False


def test_official_total_must_reconcile_with_question_marks():
    questions = [question("Q1", 5)]
    responses = [response("Q1", "answered", 5, True)]

    result = _attempt_metrics(questions, responses, official_total_marks=10)

    assert result["marks_reconciliation_ok"] is False
    assert result["report_ready"] is False



def test_duplicate_error_tags_do_not_inflate_question_code_frequency():
    rows = [
        {"question_id": "Q1", "error_code": "C01", "comment": "Arithmetic"},
        {"question_id": "Q1", "error_code": "C01", "comment": "Duplicate tag"},
        {"question_id": "Q1", "error_code": "C04", "comment": "Sign"},
        {"question_id": "Q2", "error_code": "C01", "comment": "Arithmetic"},
    ]

    unique = _unique_error_rows(rows)

    assert len(unique) == 3
    assert Counter(row["error_code"] for row in unique) == {"C01": 2, "C04": 1}


def test_recurring_error_requires_a_distinct_prior_assessment():
    current = Counter({"C01": 3, "C02": 2})
    previous = {
        "C01": {"question_count": 4, "assessment_count": 0},
        "C02": {"question_count": 2, "assessment_count": 1},
    }

    recurring = _build_recurring_errors(current, previous)

    assert [item["code"] for item in recurring] == ["C02"]
    assert recurring[0]["prior_assessments"] == 1



def test_marks_above_question_maximum_block_final_report():
    questions = [question("Q1", 5)]
    responses = [response("Q1", "answered", 6, True)]

    result = _attempt_metrics(questions, responses, official_total_marks=5)

    assert result["marks_within_bounds"] is False
    assert result["invalid_mark_question_ids"] == ["Q1"]
    assert result["report_ready"] is False
