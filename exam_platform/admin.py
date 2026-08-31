"""Functional teacher/admin interface for managing the assessment question bank."""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from .models import Question, Test, ContentBlock
from .storage import storage

admin_bp = Blueprint("admin", __name__, url_prefix="/teacher")


def _next_question_id():
    existing = list(storage.questions.keys())
    numbers = []
    for qid in existing:
        if qid.startswith("Q") and qid[1:].isdigit():
            numbers.append(int(qid[1:]))
    return f"Q{(max(numbers, default=0) + 1):04d}"


def _next_test_id():
    existing = list(storage.tests.keys())
    numbers = []
    for tid in existing:
        if tid.startswith("TEST") and tid[4:].isdigit():
            numbers.append(int(tid[4:]))
    return f"TEST{(max(numbers, default=0) + 1):03d}"


def _question_from_form(question_id, existing=None):
    question_type = request.form.get("question_type", "mcq").strip()
    answer_mode = (
        "final_answer_selection_and_handwritten_upload"
        if question_type == "subjective"
        else "option_selection"
    )
    choices = [request.form.get(f"choice_{letter}", "").strip() for letter in "ABCD"]
    choices = [c for c in choices if c]
    correct = request.form.get("correct_answer", "").strip().upper() or None
    marks = float(request.form.get("marks", "1"))
    source_year = request.form.get("source_year", "").strip()
    content = [ContentBlock("text", request.form.get("question_text", "").strip())]
    return Question(
        question_id=question_id,
        question_type=question_type,
        answer_mode=answer_mode,
        question_content=content,
        answer_choices=choices,
        correct_answer=correct,
        marks=marks,
        handwritten_upload_mode=request.form.get("handwritten_upload_mode", "none"),
        subject=request.form.get("subject", "Mathematics").strip() or "Mathematics",
        board=request.form.get("board", "").strip() or None,
        class_level=int(request.form["class_level"]) if request.form.get("class_level") else None,
        chapter=request.form.get("chapter", "").strip() or None,
        topic=request.form.get("topic", "").strip() or None,
        subtopic=request.form.get("subtopic", "").strip() or None,
        difficulty=request.form.get("difficulty", "").strip() or None,
        competency=request.form.get("competency", "").strip() or None,
        source=request.form.get("source", "").strip() or None,
        source_year=int(source_year) if source_year.isdigit() else None,
    )


@admin_bp.route("/")
def dashboard():
    return render_template("teacher_dashboard.html", questions=list(storage.questions.values()), tests=list(storage.tests.values()))


@admin_bp.route("/questions")
def questions():
    query = request.args.get("q", "").strip().lower()
    question_type = request.args.get("type", "").strip()
    board = request.args.get("board", "").strip()
    class_level = request.args.get("class_level", "").strip()
    items = list(storage.questions.values())
    if query:
        items = [q for q in items if query in q.question_id.lower() or query in (q.chapter or "").lower() or query in (q.topic or "").lower() or query in str(q.question_content[0].value).lower()]
    if question_type:
        items = [q for q in items if q.question_type == question_type]
    if board:
        items = [q for q in items if (q.board or "") == board]
    if class_level:
        items = [q for q in items if str(q.class_level or "") == class_level]
    return render_template("teacher_questions.html", questions=items, query=query, question_type=question_type, board=board, class_level=class_level)


@admin_bp.route("/questions/new", methods=["GET", "POST"])
def add_question():
    if request.method == "POST":
        question_id = _next_question_id()
        q = _question_from_form(question_id)
        if not q.question_content[0].value:
            flash("Question text is required.", "error")
            return render_template("teacher_question_form.html", question=q, is_edit=False)
        if not q.answer_choices or not q.correct_answer or q.correct_answer not in {chr(65 + i) for i in range(len(q.answer_choices))}:
            flash("Add answer choices and select a valid correct answer.", "error")
            return render_template("teacher_question_form.html", question=q, is_edit=False)
        storage.create_question(q)
        flash(f"Question {question_id} saved.", "success")
        return redirect(url_for("admin.questions"))
    return render_template("teacher_question_form.html", question=None, is_edit=False)


@admin_bp.route("/questions/<question_id>/edit", methods=["GET", "POST"])
def edit_question(question_id):
    q = storage.get_question(question_id)
    if not q:
        return "Question not found", 404
    if request.method == "POST":
        updated = _question_from_form(question_id, q)
        if not updated.question_content[0].value:
            flash("Question text is required.", "error")
            return render_template("teacher_question_form.html", question=updated, is_edit=True)
        if not updated.answer_choices or not updated.correct_answer or updated.correct_answer not in {chr(65 + i) for i in range(len(updated.answer_choices))}:
            flash("Add answer choices and select a valid correct answer.", "error")
            return render_template("teacher_question_form.html", question=updated, is_edit=True)
        storage.create_question(updated)
        flash(f"Question {question_id} updated.", "success")
        return redirect(url_for("admin.questions"))
    return render_template("teacher_question_form.html", question=q, is_edit=True)


@admin_bp.route("/questions/<question_id>/delete", methods=["POST"])
def delete_question(question_id):
    if not storage.get_question(question_id):
        return "Question not found", 404
    try:
        storage.delete_question(question_id)
        flash(f"Question {question_id} deleted.", "success")
    except Exception as exc:
        flash(f"Question could not be deleted because it is already used: {exc}", "error")
    return redirect(url_for("admin.questions"))


@admin_bp.route("/tests")
def tests():
    return render_template("teacher_tests.html", tests=list(storage.tests.values()), questions=list(storage.questions.values()))


@admin_bp.route("/tests/new", methods=["GET", "POST"])
def add_test():
    if request.method == "POST":
        selected = request.form.getlist("question_ids")
        selected = [qid for qid in selected if qid in storage.questions]
        if not selected:
            flash("Select at least one question.", "error")
            return render_template("teacher_test_form.html", questions=list(storage.questions.values()), form=request.form)
        test_id = _next_test_id()
        duration = int(request.form.get("duration_minutes", "60"))
        test = Test(
            test_id=test_id,
            title=request.form.get("title", "").strip() or test_id,
            subject=request.form.get("subject", "Mathematics").strip() or "Mathematics",
            class_level=int(request.form.get("class_level", "10")),
            duration_minutes=duration,
            total_marks=sum(storage.questions[qid].marks for qid in selected),
            questions=selected,
            status=request.form.get("status", "active"),
            board=request.form.get("board", "").strip() or None,
            test_date=request.form.get("test_date") or None,
            test_type=request.form.get("test_type", "weekly").strip() or "weekly",
        )
        storage.create_test(test)
        flash(f"Test {test_id} created with {len(selected)} questions.", "success")
        return redirect(url_for("admin.tests"))
    return render_template("teacher_test_form.html", questions=list(storage.questions.values()), form={})


def register_admin(app):
    app.register_blueprint(admin_bp)
