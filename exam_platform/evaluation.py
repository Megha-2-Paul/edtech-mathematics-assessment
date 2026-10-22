"""Teacher evaluation workflow, diagnosis, and student result calculations."""

import math
import os
from io import BytesIO
from pathlib import Path
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, send_file, send_from_directory, url_for
from sqlalchemy import text

from database import engine
from .db_source import storage
from .diagnosis import diagnose_attempt
from .diagnostic_rules_adapter import add_diagnostic_interpretation
from .reporting import build_report


evaluation_bp = Blueprint("evaluation", __name__)

ERROR_CODES = [
    ("C01", "Calculation"),
    ("C02", "Conceptual"),
    ("C03", "Formula"),
    ("C04", "Sign"),
    ("C05", "Incomplete steps"),
    ("C06", "Wrong method"),
    ("C07", "Missing justification"),
    ("C08", "Misunderstood question"),
    ("C09", "Time/attempt"),
]


def _attempt_or_404(attempt_id):
    attempt = storage.get_attempt(attempt_id)
    if not attempt:
        abort(404)
    return attempt

@evaluation_bp.route("/teacher/attempt/<attempt_id>/image/<image_id>")
def teacher_answer_image(attempt_id, image_id):
    """Serve an answer image only through the authenticated teacher route."""
    attempt = _attempt_or_404(attempt_id)
    image = next(
        (
            item for item in storage.images.values()
            if item.image_id == image_id and item.attempt_id == attempt_id
        ),
        None,
    )
    if not image:
        abort(404)

    try:
        from .media import read_stored_image

        data, content_type = read_stored_image(image.file_path)
    except FileNotFoundError:
        abort(404, description="Stored answer image is missing")
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Failed to retrieve teacher answer image for attempt %s", attempt_id
        )
        abort(503, description="Stored answer image is temporarily unavailable")

    return send_file(BytesIO(data), mimetype=content_type, max_age=0)


def _evaluation_errors(response_id):
    with engine.connect() as db:
        return db.execute(
            text(
                "SELECT error_code, comment, marks_lost "
                "FROM evaluation_errors "
                "WHERE response_id=:id "
                "ORDER BY evaluation_error_id"
            ),
            {"id": response_id},
        ).mappings().all()


def _evaluate_attempt(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = storage.get_attempt_responses(attempt_id)

    question_map = {q.question_id: q for q in questions}
    response_map = {
        r.question_id: r for r in responses if r.question_id in question_map
    }
    total = float(getattr(test, "total_marks", 0) or 0)
    question_total = sum(float(q.marks) for q in questions)
    if total <= 0:
        total = question_total
    awarded = sum(
        float(response_map[qid].marks_awarded or 0)
        for qid in question_map
        if qid in response_map and response_map[qid].marks_awarded is not None
    )
    attempted_ids = {
        qid for qid, response in response_map.items()
        if str(response.answer_status).lower() in {"answered", "partial"}
    }
    attempted_available = sum(float(question_map[qid].marks) for qid in attempted_ids)
    attempted_awarded = sum(
        float(response_map[qid].marks_awarded or 0)
        for qid in attempted_ids
        if response_map[qid].marks_awarded is not None
    )

    attempt.score = round(awarded, 2)
    attempt.percentage = round(awarded / total * 100, 2) if total > 0 else None
    attempt.attempt_rate = round(len(attempted_ids) / len(questions) * 100, 2) if questions else None
    attempt.accuracy = (
        round(attempted_awarded / attempted_available * 100, 2)
        if attempted_available > 0 else None
    )

    if attempt.submitted_at:
        attempt.time_taken_seconds = max(
            0,
            int((attempt.submitted_at - attempt.started_at).total_seconds()),
        )

    return attempt


def _save_response_evaluation(db, response, question, marks, error_codes, comment):
    marks = max(0.0, min(float(marks), float(question.marks)))
    is_correct = (
        (response.selected_answer == question.correct_answer)
        if question.question_type == "mcq" and response.selected_answer
        else (
            marks >= float(question.marks)
            if question.question_type != "mcq"
            else False
        )
    )

    db.execute(
        text(
            "UPDATE responses "
            "SET marks_awarded=:marks,is_correct=:correct "
            "WHERE response_id=:id"
        ),
        {
            "marks": marks,
            "correct": is_correct,
            "id": response.response_id,
        },
    )
    db.execute(
        text("DELETE FROM evaluation_errors WHERE response_id=:id"),
        {"id": response.response_id},
    )

    lost = max(0.0, float(question.marks) - marks)
    for code in error_codes:
        db.execute(
            text(
                "INSERT INTO evaluation_errors "
                "(response_id,error_code,comment,marks_lost) "
                "VALUES(:response,:code,:comment,:lost)"
            ),
            {
                "response": response.response_id,
                "code": code,
                "comment": comment or None,
                "lost": lost if len(error_codes) == 1 else None,
            },
        )


def _update_question_history(attempt_id, increment_counts=True):
    attempt = storage.get_attempt(attempt_id)
    responses = storage.get_attempt_responses(attempt_id)

    with engine.begin() as db:
        for response in responses:
            errors = db.execute(
                text(
                    "SELECT error_code FROM evaluation_errors "
                    "WHERE response_id=:id ORDER BY evaluation_error_id"
                ),
                {"id": response.response_id},
            ).scalars().all()
            summary = ", ".join(errors) if errors else None

            db.execute(
                text(
                    """INSERT INTO question_history(
student_id,question_id,attempt_count,correct_count,last_attempted_at,last_correct_at,last_marks_awarded,last_error_summary)
VALUES(:student,:question,1,:correct,:attempted,:correct_at,:marks,:summary)
ON DUPLICATE KEY UPDATE attempt_count=attempt_count+IF(:increment_counts,1,0),correct_count=correct_count+IF(:increment_counts,VALUES(correct_count),0),last_attempted_at=VALUES(last_attempted_at),last_correct_at=IF(VALUES(correct_count)=1,VALUES(last_correct_at),last_correct_at),last_marks_awarded=VALUES(last_marks_awarded),last_error_summary=VALUES(last_error_summary)"""
                ),
                {
                    "student": attempt.student_id,
                    "question": response.question_id,
                    "correct": 1 if response.is_correct else 0,
                    "attempted": attempt.submitted_at or datetime.now(),
                    "correct_at": attempt.submitted_at if response.is_correct else None,
                    "marks": response.marks_awarded,
                    "summary": summary,
                    "increment_counts": 1 if increment_counts else 0,
                },
            )


@evaluation_bp.route("/teacher/submissions")
def submissions():
    test_id = request.args.get("test_id", "").strip()
    with engine.connect() as db:
        query = """SELECT a.attempt_id,a.student_id,a.test_id,a.started_at,a.submitted_at,a.status,a.score,a.percentage,t.title,s.name AS student_name
FROM attempts a JOIN tests t ON t.test_id=a.test_id JOIN students s ON s.student_id=a.student_id
WHERE a.status='submitted'"""
        params = {}
        if test_id:
            query += " AND a.test_id=:test_id"
            params["test_id"] = test_id
        query += " ORDER BY COALESCE(a.submitted_at,a.started_at) DESC"
        rows = db.execute(text(query), params).mappings().all()

    selected_test = storage.get_test(test_id) if test_id else None
    return render_template(
        "teacher_submissions.html",
        submissions=rows,
        selected_test=selected_test,
        selected_test_id=test_id,
    )


@evaluation_bp.route("/teacher/evaluate/<attempt_id>", methods=["GET", "POST"])
def evaluate(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = {r.question_id: r for r in storage.get_attempt_responses(attempt_id)}

    if request.method == "POST":
        # Validate the entire evaluation before writing anything. An omitted
        # marks field must never silently become zero and make a partial
        # evaluation look complete to the student report.
        prepared = {}
        allowed_error_codes = {code for code, _ in ERROR_CODES}
        for q in questions:
            r = responses.get(q.question_id)
            if not r:
                flash(
                    f"Evaluation incomplete: response for {q.question_id} is missing. Nothing was saved.",
                    "error",
                )
                return redirect(url_for("evaluation.evaluate", attempt_id=attempt_id))

            if q.question_type == "mcq":
                marks = float(q.marks) if r.selected_answer == q.correct_answer else 0.0
                codes = []
            else:
                raw_marks = request.form.get(f"marks_{q.question_id}")
                if raw_marks is None or not raw_marks.strip():
                    flash(
                        f"Evaluation incomplete: enter marks for every written-response question. Nothing was saved ({q.question_id} is missing).",
                        "error",
                    )
                    return redirect(url_for("evaluation.evaluate", attempt_id=attempt_id))
                try:
                    marks = float(raw_marks)
                except (TypeError, ValueError):
                    flash(
                        f"Invalid marks for {q.question_id}. Use a number within the allowed range. Nothing was saved.",
                        "error",
                    )
                    return redirect(url_for("evaluation.evaluate", attempt_id=attempt_id))
                if not math.isfinite(marks) or marks < 0 or marks > float(q.marks):
                    flash(
                        f"Invalid marks for {q.question_id}. Marks must be between 0 and {q.marks}. Nothing was saved.",
                        "error",
                    )
                    return redirect(url_for("evaluation.evaluate", attempt_id=attempt_id))
                codes = [
                    c for c in request.form.getlist(f"errors_{q.question_id}")
                    if c in allowed_error_codes
                ]

            prepared[q.question_id] = (
                r,
                q,
                marks,
                codes,
                request.form.get(f"comment_{q.question_id}", "").strip(),
            )

        was_previously_evaluated = bool(responses) and all(
            r.marks_awarded is not None for r in responses.values()
        )
        # Persist all marks and error codes in one transaction. A database
        # failure must not leave a partly evaluated submission behind.
        with engine.begin() as db:
            for r, q, marks, codes, comment in prepared.values():
                _save_response_evaluation(db, r, q, marks, codes, comment)

        attempt = _evaluate_attempt(attempt_id)
        storage.update_attempt(attempt)
        # Revisions update the latest diagnosis but must not count the same
        # submitted attempt as another historical attempt.
        _update_question_history(
            attempt_id, increment_counts=not was_previously_evaluated
        )
        flash("Evaluation saved and result calculated.", "success")
        return redirect(url_for("evaluation.evaluate", attempt_id=attempt_id))

    response_data = []
    for q in questions:
        r = responses.get(q.question_id)
        images = storage.get_attempt_images(attempt_id, q.question_id)
        response_data.append(
            {
                "question": q,
                "response": r,
                "errors": _evaluation_errors(r.response_id) if r else [],
                "handwritten_upload_mode": q.handwritten_upload_mode,
                "images": [
                    {
                        "url": url_for(
                            "evaluation.teacher_answer_image",
                            attempt_id=attempt_id,
                            image_id=image.image_id,
                        ),
                        "page_number": image.page_number,
                        "name": image.original_filename,
                    }
                    for image in images
                ],
            }
        )

    return render_template(
        "teacher_evaluation.html",
        attempt=attempt,
        test=test,
        response_data=response_data,
        error_codes=ERROR_CODES,
    )


def _student_report(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = storage.get_attempt_responses(attempt_id)
    student = storage.get_student(attempt.student_id)

    diagnosis = add_diagnostic_interpretation(
        diagnose_attempt(attempt, test, questions, responses)
    )
    return build_report(diagnosis, student, test, attempt)


@evaluation_bp.route("/result/<attempt_id>")
def student_result(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    if attempt.student_id != session.get("student_id"):
        return "Access denied", 403
    if attempt.status != "submitted":
        return redirect(url_for("test_listing"))

    test = storage.get_test(attempt.test_id)
    questions = storage.get_questions(test.questions)
    responses = storage.get_attempt_responses(attempt_id)
    response_map = {r.question_id: r for r in responses}
    error_map = {}

    with engine.connect() as db:
        rows = db.execute(
            text(
                "SELECT r.question_id,e.error_code,e.comment "
                "FROM evaluation_errors e "
                "JOIN responses r ON r.response_id=e.response_id "
                "WHERE r.attempt_id=:attempt "
                "ORDER BY e.evaluation_error_id"
            ),
            {"attempt": attempt_id},
        ).mappings().all()

    for row in rows:
        error_map.setdefault(row["question_id"], []).append(row)

    report = _student_report(attempt_id)
    diagnosis = report["diagnosis"]
    attempt.score = diagnosis["score"]
    attempt.percentage = diagnosis["percentage"]
    attempt.attempt_rate = diagnosis["attempt_rate"]

    return render_template(
        "student_result.html",
        attempt=attempt,
        test=test,
        questions=questions,
        response_map=response_map,
        error_map=error_map,
        diagnosis=diagnosis,
        report=report,
    )


@evaluation_bp.route("/report/<attempt_id>")
def student_report(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    if attempt.student_id != session.get("student_id"):
        return "Access denied", 403
    if attempt.status != "submitted":
        return redirect(url_for("test_listing"))

    report = _student_report(attempt_id)
    if not report["diagnosis"]["report_ready"]:
        return render_template("student_report.html", report=report, awaiting=True)

    return render_template("student_report.html", report=report, awaiting=False)


@evaluation_bp.route("/report/<attempt_id>/pdf")
def student_report_pdf(attempt_id):
    attempt = _attempt_or_404(attempt_id)
    if attempt.student_id != session.get("student_id"):
        return "Access denied", 403
    if attempt.status != "submitted":
        return redirect(url_for("test_listing"))

    report = _student_report(attempt_id)
    if not report["diagnosis"]["report_ready"]:
        return "Report is not ready: evaluation or data validation is incomplete.", 409

    from .report_pdf import render_report_pdf

    try:
        pdf_buffer = render_report_pdf(report)
    except (ValueError, RuntimeError):
        app_logger = __import__("logging").getLogger(__name__)
        app_logger.exception("Failed to generate student report PDF for attempt %s", attempt_id)
        return "Report could not be generated. Please try again later.", 500

    filename = f"Improvia_Report_{attempt.student_id}_{attempt.test_id}.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


def register_evaluation(app):
    app.register_blueprint(evaluation_bp)
    existing_uploaded_file = app.view_functions.get("uploaded_file")
    if existing_uploaded_file:
        upload_folder = app.config["UPLOAD_FOLDER"]

        def serve_uploaded_file(filename):
            requested_stem = Path(filename).stem
            for image in storage.images.values():
                stored_name = Path(str(image.file_path or "")).name
                if filename == stored_name or requested_stem == stored_name:
                    return "Answer images must be accessed through an authenticated assessment route.", 403
            return send_from_directory(upload_folder, filename)

        app.view_functions["uploaded_file"] = serve_uploaded_file
