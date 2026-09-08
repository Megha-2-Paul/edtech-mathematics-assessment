"""Review route for saving explicit OR alternatives as separate canonical questions."""
from __future__ import annotations

from flask import Blueprint, jsonify, redirect, url_for, request

from question_bank.extraction.or_question_splitter import split_or_parts
from question_bank.extraction.question_asset_persistence import persist_source_visuals
from question_bank.extraction.review_app import (
    _field,
    _find_item,
    _load_review,
    _normalise_pages,
    _parse_json_field,
    _question_from_extraction,
    _save_review,
    _source_pdf,
)
from exam_platform.storage import storage

or_bp = Blueprint("extraction_or_review", __name__, url_prefix="/teacher/extraction-review")


@or_bp.route("/<path:item_id>/split-or", methods=["POST"])
def split_or_review(item_id: str):
    _path, data, question = _find_item(item_id)
    current = _load_review(item_id)
    if current.get("status") == "APPROVED":
        return redirect(url_for("extraction_review.item", item_id=item_id))

    names = (
        "question_text", "marks", "question_type", "answer_mode",
        "handwritten_upload_mode", "subject", "board", "class_level",
        "chapter", "topic", "subtopic", "difficulty", "competency",
        "correct_answer", "source_year", "diagram_reference",
    )
    parent = {name: request.form.get(name, "") for name in names}
    try:
        parent["answer_choices"] = _parse_json_field(
            request.form.get("answer_choices", "[]"), "Answer choices", []
        )
        parent["question_parts"] = _parse_json_field(
            request.form.get("question_parts", "[]"), "Question parts", []
        )
        parent["assets"] = _parse_json_field(
            request.form.get("assets", "[]"), "Assets", []
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    alternatives = split_or_parts(parent["question_text"], parent["question_parts"])
    if len(alternatives) < 2:
        return jsonify({
            "error": "This item does not contain at least two explicit OR alternatives."
        }), 400
    if not parent["chapter"].strip():
        return jsonify({"error": "Chapter must be verified before approval."}), 400

    created_ids: list[str] = []
    created_labels: list[str] = []
    source_pdf = _source_pdf(data, question)
    source_page = int(_normalise_pages(question)[0])
    base_source_number = str(
        _field(question, "source_question_number", "question_number", "number", default="")
    ).strip()

    try:
        for alternative in alternatives:
            identifier = alternative["part_identifier"]
            marks = alternative["marks"] if alternative["marks"] not in (None, "") else parent["marks"]
            question_type = alternative["question_type"] or parent["question_type"]
            correct_answer = (
                alternative["correct_answer"]
                if alternative["correct_answer"] not in (None, "")
                else parent["correct_answer"]
            )
            answer_choices = alternative["answer_choices"] or []
            if not answer_choices:
                answer_choices = parent["answer_choices"]
            if str(question_type).strip().lower() == "mcq" and not str(correct_answer or "").strip():
                raise ValueError(
                    f"Correct answer must be verified for OR alternative ({identifier}) because it is an MCQ."
                )
            if marks in (None, ""):
                raise ValueError(f"Marks must be verified for OR alternative ({identifier}).")

            child = dict(parent)
            child.update({
                "question_text": f"({identifier}) {alternative['question_text']}",
                "question_parts": [],
                "marks": marks,
                "question_type": question_type,
                "answer_mode": alternative["answer_mode"] or parent["answer_mode"],
                "handwritten_upload_mode": alternative["handwritten_upload_mode"] or parent["handwritten_upload_mode"],
                "answer_choices": answer_choices,
                "correct_answer": correct_answer,
                "diagram_reference": alternative["diagram_reference"] or "",
                "assets": alternative["assets"] or [],
            })
            qobj = _question_from_extraction(question, data, child)
            storage.create_question(qobj)
            created_ids.append(qobj.question_id)
            created_labels.append(f"{base_source_number}({identifier}) → {qobj.question_id}")

            # Only persist a visual for the alternative that explicitly owns it.
            # This prevents a diagram belonging to part (b) being copied onto part (a).
            if alternative["diagram_reference"] or alternative["assets"]:
                try:
                    persist_source_visuals(
                        source_pdf,
                        source_page,
                        base_source_number,
                        qobj.question_id,
                    )
                except Exception as exc:
                    # Keep the question approved, but retain the warning for human follow-up.
                    created_labels[-1] += f" [visual warning: {exc}]"
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc), "created_question_ids": created_ids}), 400

    note = request.form.get("note", "").strip()
    summary = "Saved as separate OR questions: " + ", ".join(created_labels)
    _save_review(
        item_id,
        "APPROVED",
        f"{note + ' ' if note else ''}{summary}",
        question_id=created_ids[0],
        question_snapshot=question,
        human_verified_values=parent,
    )
    review_path = _path = url_for("extraction_review.item", item_id=item_id)
    return redirect(review_path)


def register_or_question_review(app):
    app.register_blueprint(or_bp)
