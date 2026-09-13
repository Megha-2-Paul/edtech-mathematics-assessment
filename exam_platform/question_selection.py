"""Deterministic question candidate ranking for future assessments."""

from collections import Counter

from sqlalchemy import text

from database import engine


def rank_question_candidates(
    student_id,
    candidate_questions,
    limit=None,
    weak_chapters=None,
    weak_topics=None,
):
    """Rank question objects without changing or creating a test."""
    weak_chapters = set(weak_chapters or [])
    weak_topics = set(weak_topics or [])

    with engine.connect() as db:
        history = db.execute(
            text(
                """
                SELECT question_id, attempt_count, last_marks_awarded,
                       last_error_summary
                FROM question_history
                WHERE student_id = :student_id
                """
            ),
            {"student_id": student_id},
        ).mappings().all()

        errors = db.execute(
            text(
                """
                SELECT e.error_code, COUNT(*) AS n
                FROM evaluation_errors e
                JOIN responses r ON r.response_id = e.response_id
                JOIN attempts a ON a.attempt_id = r.attempt_id
                WHERE a.student_id = :student_id
                  AND a.status = 'submitted'
                GROUP BY e.error_code
                """
            ),
            {"student_id": student_id},
        ).mappings().all()

    history_map = {row["question_id"]: row for row in history}
    error_counts = Counter(
        {row["error_code"]: int(row["n"]) for row in errors}
    )
    ranked = []

    for question in candidate_questions:
        history_row = history_map.get(question.question_id)
        score = 0
        reasons = []

        if not history_row:
            score += 50
            reasons.append("new question")
        else:
            score -= min(30, int(history_row["attempt_count"]) * 10)

            if (
                history_row["last_marks_awarded"] is not None
                and float(history_row["last_marks_awarded"] or 0)
                < float(question.marks)
            ):
                score += 25
                reasons.append("reassess previous gap")

            if history_row["last_error_summary"]:
                score += 15
                reasons.append("targets previous error")

        if question.chapter in weak_chapters:
            score += 20
            reasons.append("weak chapter")

        if question.topic in weak_topics:
            score += 15
            reasons.append("weak topic")

        if getattr(question, "status", "active") != "active":
            score -= 100

        ranked.append((score, question, reasons))

    ranked.sort(
        key=lambda item: (
            item[0],
            getattr(item[1], "marks", 0),
        ),
        reverse=True,
    )

    if limit is not None:
        ranked = ranked[:limit]

    return [
        {
            "question": question,
            "score": score,
            "reasons": reasons,
        }
        for score, question, reasons in ranked
    ]
