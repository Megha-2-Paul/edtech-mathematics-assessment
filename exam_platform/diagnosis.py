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


def _previous_attempts(student_id, current_attempt_id):
    with engine.connect() as db:
        return db.execute(
            text(
                """
                SELECT attempt_id, test_id, submitted_at, score, percentage,
                       attempt_rate, accuracy
                FROM attempts
                WHERE student_id = :student_id
                  AND attempt_id <> :current_attempt_id
                  AND status = 'submitted'
                ORDER BY submitted_at DESC
                """
            ),
            {
                "student_id": student_id,
                "current_attempt_id": current_attempt_id,
            },
        ).mappings().all()


def _previous_error_counts(student_id, current_attempt_id):
    with engine.connect() as db:
        rows = db.execute(
            text(
                """
                SELECT e.error_code, COUNT(*) AS error_count
                FROM evaluation_errors e
                JOIN responses r ON r.response_id = e.response_id
                JOIN attempts a ON a.attempt_id = r.attempt_id
                WHERE a.student_id = :student_id
                  AND a.attempt_id <> :current_attempt_id
                  AND a.status = 'submitted'
                GROUP BY e.error_code
                ORDER BY error_count DESC
                """
            ),
            {
                "student_id": student_id,
                "current_attempt_id": current_attempt_id,
            },
        ).mappings().all()

    return {row["error_code"]: int(row["error_count"]) for row in rows}


def diagnose_attempt(attempt, test, questions, responses):
    """Return a template-friendly deterministic diagnostic dictionary."""
    response_map = {response.question_id: response for response in responses}
    errors = _error_rows(attempt.attempt_id)

    total_marks = sum(_num(question.marks) for question in questions)
    awarded = sum(_num(response.marks_awarded) for response in responses)
    attempted = sum(
        1
        for response in responses
        if response.answer_status == "answered"
    )
    correct = sum(1 for response in responses if response.is_correct is True)
    evaluated = sum(
        1
        for question in questions
        if not response_map.get(question.question_id)
        or response_map[question.question_id].marks_awarded is not None
    )
    marks_lost = max(0.0, total_marks - awarded)

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
            response and response.answer_status == "answered"
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
    )
    previous_errors = _previous_error_counts(
        attempt.student_id,
        attempt.attempt_id,
    )

    recurring_errors = [
        {
            "code": code,
            "label": ERROR_LABELS.get(code, code),
            "current_count": count,
            "previous_count": previous_errors.get(code, 0),
        }
        for code, count in error_counts.most_common()
        if previous_errors.get(code, 0) > 0
    ]

    previous_score = previous[0]["score"] if previous else None
    score_change = (
        round(awarded - _num(previous_score), 2)
        if previous_score is not None
        else None
    )
    percentage_change = (
        round(
            _num(attempt.percentage) - _num(previous[0]["percentage"]),
            2,
        )
        if previous
        else None
    )

    return {
        "total_marks": round(total_marks, 2),
        "score": round(awarded, 2),
        "percentage": (
            round(awarded / total_marks * 100, 2)
            if total_marks
            else 0
        ),
        "marks_lost": round(marks_lost, 2),
        "attempted": attempted,
        "total_questions": len(questions),
        "attempt_rate": (
            round(attempted / len(questions) * 100, 2)
            if questions
            else 0
        ),
        "accuracy": round(correct / attempted * 100, 2) if attempted else 0,
        "evaluated_responses": evaluated,
        "evaluation_complete": evaluated >= len(questions),
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
        "score_change": score_change,
        "percentage_change": percentage_change,
        "history": [dict(row) for row in reversed(previous)],
    }
