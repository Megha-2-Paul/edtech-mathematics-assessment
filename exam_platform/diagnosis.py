"""Deterministic performance diagnosis for the Mathematics Assessment MVP.

This module deliberately avoids AI. It converts evaluated attempt data into
student-facing diagnostic signals: marks lost, error patterns, chapter/topic
performance, strengths, weaknesses, recurring errors, and comparison data.
"""

from collections import Counter, defaultdict

from sqlalchemy import text

from database import engine


ERROR_LABELS = {
    "C01": "Calculation",
    "C02": "Conceptual",
    "C03": "Formula",
    "C04": "Sign",
    "C05": "Incomplete steps",
    "C06": "Wrong method",
    "C07": "Missing justification",
    "C08": "Misunderstood question",
    "C09": "Time/attempt",
}


def _num(value, default=0.0):
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def _error_rows(attempt_id):
    with engine.connect() as db:
        return db.execute(
            text(
                """
                SELECT r.question_id, e.error_code, e.comment
                FROM evaluation_errors e
                JOIN responses r ON r.response_id = e.response_id
                WHERE r.attempt_id = :attempt_id
                ORDER BY e.evaluation_error_id
                """
            ),
            {"attempt_id": attempt_id},
        ).mappings().all()


def _previous_attempts(student_id, current_attempt_id, current_test):
    """Previous submitted assessments for the same subject/class/board only."""
    with engine.connect() as db:
        return db.execute(
            text(
                """
                SELECT a.attempt_id, a.test_id, a.submitted_at, a.score, a.percentage,
                       a.attempt_rate, a.accuracy, t.subject, t.class_level, t.board
                FROM attempts a
                JOIN tests t ON t.test_id = a.test_id
                WHERE a.student_id = :student_id
                  AND a.attempt_id <> :current_attempt_id
                  AND a.status = 'submitted'
                  AND t.subject = :subject
                  AND t.class_level = :class_level
                  AND ((t.board = :board) OR (t.board IS NULL AND :board IS NULL))
                ORDER BY a.submitted_at DESC
                """
            ),
            {
                "student_id": student_id,
                "current_attempt_id": current_attempt_id,
                "subject": getattr(current_test, "subject", "Mathematics"),
                "class_level": getattr(current_test, "class_level", None),
                "board": getattr(current_test, "board", None),
            },
        ).mappings().all()


def _previous_error_history(student_id, current_attempt_id, current_test):
    """Return error history restricted to the same subject/class/board."""
    with engine.connect() as db:
        rows = db.execute(
            text(
                """
                SELECT e.error_code,
                       COUNT(DISTINCT r.question_id) AS question_count,
                       COUNT(DISTINCT a.attempt_id) AS assessment_count
                FROM evaluation_errors e
                JOIN responses r ON r.response_id = e.response_id
                JOIN attempts a ON a.attempt_id = r.attempt_id
                JOIN tests t ON t.test_id = a.test_id
                WHERE a.student_id = :student_id
                  AND a.attempt_id <> :current_attempt_id
                  AND a.status = 'submitted'
                  AND t.subject = :subject
                  AND t.class_level = :class_level
                  AND ((t.board = :board) OR (t.board IS NULL AND :board IS NULL))
                GROUP BY e.error_code
                """
            ),
            {
                "student_id": student_id,
                "current_attempt_id": current_attempt_id,
                "subject": getattr(current_test, "subject", "Mathematics"),
                "class_level": getattr(current_test, "class_level", None),
                "board": getattr(current_test, "board", None),
            },
        ).mappings().all()
    return {
        row["error_code"]: {
            "question_count": int(row["question_count"]),
            "assessment_count": int(row["assessment_count"]),
        }
        for row in rows
    }


def _attempt_metrics(questions, responses, official_total_marks=None):
    """Calculate report metrics from explicit response status and evaluated marks.

    Missing response rows or missing awarded marks are not treated as evaluated.
    Attempted-work accuracy is marks earned / marks available on attempted work.
    """
    question_map = {q.question_id: q for q in questions}
    response_map = {
        r.question_id: r for r in responses if r.question_id in question_map
    }
    question_marks = sum(_num(q.marks) for q in questions)
    total_marks = _num(official_total_marks, question_marks)
    if total_marks <= 0:
        total_marks = question_marks
    earned = sum(
        _num(response_map[qid].marks_awarded)
        for qid in question_map
        if qid in response_map and response_map[qid].marks_awarded is not None
    )
    attempted_ids = {
        qid for qid, response in response_map.items()
        if str(response.answer_status).lower() in {"answered", "partial"}
    }
    attempted_available = sum(_num(question_map[qid].marks) for qid in attempted_ids)
    unattempted_available = sum(
        _num(question_map[qid].marks)
        for qid, response in response_map.items()
        if str(response.answer_status).lower() == "unanswered"
    )
    attempted_earned = sum(
        _num(response_map[qid].marks_awarded)
        for qid in attempted_ids
        if response_map[qid].marks_awarded is not None
    )
    evaluated = sum(
        1 for qid in question_map
        if qid in response_map and response_map[qid].marks_awarded is not None
    )
    missing_response_ids = sorted(set(question_map) - set(response_map))
    unevaluated_ids = sorted(
        qid for qid, response in response_map.items()
        if response.marks_awarded is None
    )
    reconciliation_ok = abs(question_marks - total_marks) < 0.01
    return {
        "question_marks": round(question_marks, 2),
        "total_marks": round(total_marks, 2),
        "score": round(earned, 2),
        "percentage": round(earned / total_marks * 100, 2) if total_marks > 0 else None,
        "attempted": len(attempted_ids),
        "unattempted": sum(
            1 for r in response_map.values()
            if str(r.answer_status).lower() == "unanswered"
        ),
        "total_questions": len(questions),
        "attempt_rate": round(len(attempted_ids) / len(questions) * 100, 2) if questions else None,
        "attempted_available_marks": round(attempted_available, 2),
        "attempted_marks_awarded": round(attempted_earned, 2),
        "unattempted_available_marks": round(unattempted_available, 2),
        "accuracy": round(attempted_earned / attempted_available * 100, 2) if attempted_available > 0 else None,
        "fully_correct_rate": round(
            sum(1 for qid in attempted_ids if response_map[qid].is_correct is True)
            / len(attempted_ids) * 100, 2
        ) if attempted_ids else None,
        "evaluated_responses": evaluated,
        "missing_response_ids": missing_response_ids,
        "unevaluated_question_ids": unevaluated_ids,
        "marks_reconciliation_ok": reconciliation_ok,
        "evaluation_complete": (
            len(questions) > 0 and evaluated == len(questions)
            and not missing_response_ids and not unevaluated_ids
        ),
        "report_ready": (
            len(questions) > 0 and evaluated == len(questions)
            and not missing_response_ids and not unevaluated_ids
            and reconciliation_ok and total_marks > 0
        ),
    }


def diagnose_attempt(attempt, test, questions, responses):
    """Return a template-friendly deterministic diagnostic dictionary."""
    response_map = {response.question_id: response for response in responses}
    errors = _error_rows(attempt.attempt_id)
    metrics = _attempt_metrics(questions, responses, getattr(test, "total_marks", None))
    total_marks = metrics["total_marks"]
    awarded = metrics["score"]
    marks_lost = max(0.0, total_marks - awarded)

    # Count unique question/code pairs so duplicate evaluator rows do not inflate frequency.
    unique_errors = {
        (row["question_id"], row["error_code"]): row for row in errors
    }
    errors = list(unique_errors.values())
    error_counts = Counter(row["error_code"] for row in errors)
    error_details = [
        {
            "code": code,
            "label": ERROR_LABELS.get(code, code),
            "count": count,
        }
        for code, count in error_counts.most_common()
    ]

    chapter_stats = defaultdict(
        lambda: {
            "max_marks": 0.0,
            "marks": 0.0,
            "questions": 0,
            "attempted": 0,
        }
    )
    topic_stats = defaultdict(
        lambda: {
            "max_marks": 0.0,
            "marks": 0.0,
            "questions": 0,
            "attempted": 0,
        }
    )

    for question in questions:
        response = response_map.get(question.question_id)
        max_marks = _num(question.marks)
        marks = _num(response.marks_awarded) if response else 0.0
        was_attempted = bool(
            response and str(response.answer_status).lower() in {"answered", "partial"}
        )

        for bucket, key in (
            (chapter_stats, question.chapter or "Unclassified"),
            (topic_stats, question.topic or "Unclassified"),
        ):
            bucket[key]["max_marks"] += max_marks
            bucket[key]["marks"] += marks
            bucket[key]["questions"] += 1
            bucket[key]["attempted"] += int(was_attempted)

    def ranked_stats(bucket):
        result = []
        for name, value in bucket.items():
            percentage = (
                value["marks"] / value["max_marks"] * 100
                if value["max_marks"]
                else 0
            )
            result.append(
                {
                    "name": name,
                    "percentage": round(percentage, 1),
                    "evidence_status": (
                        "insufficient_evidence"
                        if value["attempted"] == 0 or value["attempted"] < 2
                        else "sufficient"
                    ),
                    **value,
                }
            )
        return sorted(
            result,
            key=lambda item: (item["percentage"], -item["max_marks"]),
        )

    chapter_analysis = ranked_stats(chapter_stats)
    topic_analysis = ranked_stats(topic_stats)

    strengths = [
        item
        for item in sorted(
            chapter_analysis,
            key=lambda item: item["percentage"],
            reverse=True,
        )
        if item["max_marks"] > 0 and item["percentage"] >= 75
    ][:3]

    weaknesses = [
        item
        for item in chapter_analysis
        if item["max_marks"] > 0 and item["percentage"] < 60
    ][:3]

    previous = _previous_attempts(
        attempt.student_id,
        attempt.attempt_id,
        test,
    )
    previous_error_history = _previous_error_history(
        attempt.student_id,
        attempt.attempt_id,
        test,
    )

    recurring_errors = [
        {
            "code": code,
            "label": ERROR_LABELS.get(code, code),
            "current_count": count,
            "previous_count": previous_error_history.get(code, {}).get("question_count", 0),
            "prior_assessments": previous_error_history.get(code, {}).get("assessment_count", 0),
        }
        for code, count in error_counts.most_common()
        if previous_error_history.get(code, {}).get("assessment_count", 0) > 0
    ]

    previous_score = previous[0]["score"] if previous else None
    marks_change = (
        round(awarded - _num(previous_score), 2)
        if previous_score is not None
        else None
    )
    percentage_change = (
        round(
            _num(metrics["percentage"]) - _num(previous[0]["percentage"]),
            2,
        )
        if previous and metrics["percentage"] is not None and previous[0]["percentage"] is not None
        else None
    )
    comparison_status = (
        "baseline" if not previous
        else "comparable" if previous[0]["test_id"] == test.test_id
        else "limited"
    )

    return {
        **metrics,
        "marks_lost": round(marks_lost, 2),
        "error_counts": error_details,
        "chapter_analysis": chapter_analysis,
        "topic_analysis": topic_analysis,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recurring_errors": recurring_errors,
        "previous_attempt_count": len(previous),
        "previous_score": previous_score,
        "previous_percentage": (
            previous[0]["percentage"] if previous else None
        ),
        "marks_change": marks_change,
        "score_change": percentage_change,
        "percentage_change": percentage_change,
        "comparison_status": comparison_status,
        "comparison_note": (
            "No prior assessment in the same subject/class/board scope."
            if not previous else
            "Same test ID; direct comparison."
            if comparison_status == "comparable" else
            "Previous assessment is in the same subject/class/board scope, but its question mix may differ; treat score changes as indicative, not definitive."
        ),
        "history": [dict(row) for row in reversed(previous)],
    }
