"""OR-question approval adapter."""
from __future__ import annotations

import json

from flask import Blueprint, jsonify, redirect, request, url_for

from exam_platform.storage import storage
from question_bank.extraction.or_question_splitter import split_or_parts
from question_bank.extraction.question_asset_persistence import persist_source_visuals
from question_bank.extraction.review_app import (
    _field,
    _find_item,
    _load_review,
    _normalise_pages,
    _parse_json_field,
    _question_from_extraction,
    _review_path,
    _save_review,
    _source_pdf,
)

or_bp = Blueprint("extraction_or_review", __name__, url_prefix="/teacher/extraction-review")


def _build_parent_values(question):
    names = (
        "question_text", "marks", "question_type", "answer_mode",
        "handwritten_upload_mode", "subject", "board", "class_level",
        "chapter", "topic", "subtopic", "difficulty", "competency",
        "correct_answer", "source_year", "diagram_reference",
    )
    values = {name: request.form.get(name, "") for name in names}
    values["answer_choices"] = _parse_json_field(
        request.form.get("answer_choices", "[]"), "Answer choices", []
    )
    values["question_parts"] = _parse_json_field(
        request.form.get("question_parts", "[]"), "Question parts", []
    )
    values["assets"] = _parse_json_field(
        request.form.get("assets", "[]"), "Assets", []
    )
    return values


def _split_and_approve(item_id: str):
    _path, data, source_question = _find_item(item_id)
    current = _load_review(item_id)
    if current.get("status") == "APPROVED":
        return None

    parent = _build_parent_values(source_question)
    if not parent["question_text"].strip() or not parent["chapter"].strip():
        return None

    alternatives = split_or_parts(parent["question_text"], parent["question_parts"])
    if len(alternatives) != 2:
        return None

    source_pdf = _source_pdf(data, source_question)
    source_page = int(_normalise_pages(source_question)[0])
    source_number = str(
        _field(source_question, "source_question_number", "question_number", "number", default="")
    ).strip()

    created_ids: list[str] = []
    labels: list[str] = []

    for alternative in alternatives:
        identifier = alternative["part_identifier"]
        question_type = alternative["question_type"] or parent["question_type"]
        marks = alternative["marks"] if alternative["marks"] not in (None, "") else parent["marks"]
        correct_answer = (
            alternative["correct_answer"]
            if alternative["correct_answer"] not in (None, "")
            else parent["correct_answer"]
        )
        answer_choices = alternative["answer_choices"] or parent["answer_choices"]

        if marks in (None, ""):
            raise ValueError(f"Marks must be verified for OR alternative ({identifier}).")
        if str(question_type).strip().lower() == "mcq" and not str(correct_answer or "").strip():
            raise ValueError(
                f"Correct answer must be verified for OR alternative ({identifier}) because it is an MCQ."
            )

        child = dict(parent)
        child.update(
            {
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
            }
        )

        qobj = _question_from_extraction(source_question, data, child)
        storage.create_question(qobj)
        created_ids.append(qobj.question_id)
        labels.append(f"{source_number}({identifier}) → {qobj.question_id}")

        # Persist a visual only for the alternative that explicitly declares one.
        if alternative["diagram_reference"] or alternative["assets"]:
            try:
                persist_source_visuals(
                    source_pdf,
                    source_page,
                    source_number,
                    qobj.question_id,
                )
            except Exception as exc:
                labels[-1] += f" [visual warning: {exc}]"

    note = request.form.get("note", "").strip()
    summary = "Saved as separate OR questions: " + ", ".join(labels)
    _save_review(
        item_id,
        "APPROVED",
        f"{note + ' ' if note else ''}{summary}",
        question_id=created_ids[0],
        question_snapshot=source_question,
        human_verified_values=parent,
    )

    # Keep the complete child mapping in the review record for auditability.
    review_path = _review_path(item_id)
    review_record = _load_review(item_id)
    review_record["question_ids"] = created_ids
    review_path.write_text(
        json.dumps(review_record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return redirect(url_for("extraction_review.item", item_id=item_id))


def _wrap_legacy_review(app):
    endpoint = "extraction_review.review"
    legacy_view = app.view_functions.get(endpoint)
    if legacy_view is None or getattr(legacy_view, "_or_aware", False):
        return

    def or_aware_review(item_id):
        if request.form.get("status", "").upper() == "APPROVED":
            try:
                result = _split_and_approve(item_id)
            except (TypeError, ValueError) as exc:
                return jsonify({"error": str(exc)}), 400
            if result is not None:
                return result
        return legacy_view(item_id)

    or_aware_review._or_aware = True
    app.view_functions[endpoint] = or_aware_review


def register_or_question_review(app):
    """Register the OR route and make normal Approve OR-aware."""
    if "extraction_or_review" not in app.blueprints:
        app.register_blueprint(or_bp)
    _wrap_legacy_review(app)
