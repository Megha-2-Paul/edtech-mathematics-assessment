"""Local human-verification interface for AI question extraction.

AI output stays separate from the canonical question bank until a human approves it.
The review form mirrors the canonical Question fields and explicitly flags inferred
metadata such as chapter/topic for human verification.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for

from exam_platform.models import ContentBlock, Question
from exam_platform.storage import storage
from question_bank.extraction.extraction_contract import (
    ALLOWED_QUESTION_TYPES,
    ALLOWED_UPLOAD_MODES,
    INFERRED_FIELDS_REQUIRE_HUMAN_VERIFICATION,
)

review_bp = Blueprint("extraction_review", __name__, url_prefix="/teacher/extraction-review")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INBOX_DIR = Path(os.getenv("EXTRACTION_INBOX_DIR", PROJECT_ROOT / "extraction_inbox"))
REVIEW_DIR = Path(os.getenv("EXTRACTION_REVIEW_DIR", PROJECT_ROOT / "extraction_reviews"))
SOURCE_DIR = Path(os.getenv("SOURCE_PDF_DIR", PROJECT_ROOT / "source_pdfs"))
PAGE_DIR = REVIEW_DIR / "page_renders"

for directory in (INBOX_DIR, REVIEW_DIR, PAGE_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read extraction JSON: {path.name}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise ValueError(f"Extraction file must contain a top-level 'questions' list: {path.name}")
    return data


def _extraction_files() -> list[Path]:
    return sorted(INBOX_DIR.glob("*.json"))


def _review_path(item_id: str) -> Path:
    return REVIEW_DIR / f"{_safe_id(item_id)}.json"


def _load_review(item_id: str) -> dict[str, Any]:
    path = _review_path(item_id)
    if not path.exists():
        return {"status": "PENDING", "updated_at": None, "note": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "PENDING", "updated_at": None, "note": ""}


def _save_review(item_id: str, status: str, note: str = "", question_id: str | None = None) -> None:
    payload = {"status": status, "updated_at": datetime.now().isoformat(), "note": note}
    if question_id:
        payload["question_id"] = question_id
    _review_path(item_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _question_text(question: dict[str, Any]) -> str:
    value = question.get("question_text", question.get("text", question.get("question")))
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value or "").strip()


def _json_text(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, indent=2)


def _source_year(source_pdf: str) -> int | None:
    match = re.search(r"(?:19|20)\d{2}", source_pdf)
    return int(match.group()) if match else None


def _field(question: dict[str, Any], name: str, *aliases: str, default: Any = None) -> Any:
    if name in question and question[name] is not None:
        return question[name]
    for alias in aliases:
        if alias in question and question[alias] is not None:
            return question[alias]
    return default


def _normalise_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_json_field(raw: str, label: str, default: Any) -> Any:
    if not raw.strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON") from exc


def _next_question_id() -> str:
    numbers = [int(qid[1:]) for qid in storage.questions if qid.startswith("Q") and qid[1:].isdigit()]
    return f"Q{max(numbers, default=0) + 1:04d}"


def _question_from_extraction(question: dict[str, Any], data: dict[str, Any], overrides: dict[str, Any]) -> Question:
    source_pdf = str(data.get("source_pdf") or data.get("source_paper") or question.get("source_pdf") or "")
    question_type = str(overrides.get("question_type") or "saq").lower()
    if question_type not in ALLOWED_QUESTION_TYPES:
        raise ValueError("Invalid question type")
    answer_mode = str(overrides.get("answer_mode") or "manual_written_answer").strip()
    upload_mode = str(overrides.get("handwritten_upload_mode") or "none").lower()
    if upload_mode not in ALLOWED_UPLOAD_MODES:
        raise ValueError("Invalid handwritten upload mode")
    try:
        marks = float(overrides.get("marks") or 0)
        class_level = int(overrides.get("class_level") or 12)
    except (TypeError, ValueError) as exc:
        raise ValueError("Marks and class must be valid numbers") from exc

    text_value = str(overrides.get("question_text") or "").strip()
    content = [ContentBlock("text", text_value)]
    diagram_reference = overrides.get("diagram_reference")
    if diagram_reference:
        content.append(ContentBlock("image", str(diagram_reference), metadata={"source_reference": str(diagram_reference)}))

    return Question(
        question_id=_next_question_id(),
        question_type=question_type,
        answer_mode=answer_mode,
        question_content=content,
        answer_choices=[str(x) for x in _normalise_list(overrides.get("answer_choices"))],
        correct_answer=overrides.get("correct_answer") or None,
        marks=marks,
        handwritten_upload_mode=upload_mode,
        subject=str(overrides.get("subject") or "Mathematics").strip(),
        board=str(overrides.get("board") or "CBSE").strip(),
        class_level=class_level,
        chapter=str(overrides.get("chapter") or "").strip() or None,
        topic=str(overrides.get("topic") or "").strip() or None,
        subtopic=str(overrides.get("subtopic") or "").strip() or None,
        difficulty=str(overrides.get("difficulty") or "").strip() or None,
        competency=str(overrides.get("competency") or "").strip() or None,
        source=source_pdf or None,
        source_year=overrides.get("source_year") or _source_year(source_pdf),
        status="active",
    )


def _review_form_values(question: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    source_pdf = str(data.get("source_pdf") or data.get("source_paper") or question.get("source_pdf") or "")
    values = {name: _field(question, name) for name in (
        "answer_mode", "handwritten_upload_mode", "subject", "board", "class_level",
        "chapter", "topic", "subtopic", "difficulty", "competency", "source_year",
        "correct_answer", "diagram_reference",
    )}
    values["question_text"] = _question_text(question)
    values["answer_choices"] = _field(question, "answer_choices", "options", default=[])
    values["question_parts"] = _field(question, "question_parts", default=[])
    values["source"] = _field(question, "source", default=source_pdf)
    values["source_pdf"] = source_pdf
    values["source_page"] = _field(question, "source_page", "page_number", "page")
    values["source_pages"] = _field(question, "source_pages", default=[])
    values["source_question_number"] = _field(question, "source_question_number", "question_number", "number")
    values["source_occurrence_id"] = _field(question, "source_occurrence_id")
    values["assets"] = _field(question, "assets", default=[])
    values["extraction_provider"] = _field(question, "extraction_provider", default=data.get("extraction_provider"))
    values["extraction_model"] = _field(question, "extraction_model", default=data.get("extraction_model"))
    values["extraction_run_id"] = _field(question, "extraction_run_id", default=data.get("extraction_run_id"))
    values["extraction_confidence"] = _field(question, "extraction_confidence", default=data.get("extraction_confidence"))
    values["extraction_warnings"] = _field(question, "extraction_warnings", default=data.get("extraction_warnings", []))
    values["question_type"] = str(_field(question, "question_type", "type", default="saq")).lower()
    return values


def _items() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in _extraction_files():
        try:
            data = _load_json(path)
        except ValueError:
            continue
        source_pdf = str(data.get("source_pdf") or data.get("source_paper") or "")
        for index, question in enumerate(data["questions"]):
            if not isinstance(question, dict):
                continue
            item_id = f"{path.stem}:{index}"
            review = _load_review(item_id)
            chapter_missing = not str(question.get("chapter") or "").strip()
            result.append({
                "item_id": item_id,
                "file": path.name,
                "source_pdf": source_pdf,
                "index": index,
                "question_number": str(_field(question, "question_number", "number", default=index + 1)),
                "page_number": _field(question, "source_page", "page_number", "page", default=1),
                "marks": question.get("marks"),
                "question_type": question.get("question_type") or question.get("type") or "",
                "status": review.get("status", "PENDING"),
                "chapter_missing": chapter_missing,
            })
    return result


def _find_item(item_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    try:
        filename, raw_index = item_id.rsplit(":", 1)
        index = int(raw_index)
    except ValueError:
        abort(404)
    path = INBOX_DIR / f"{filename}.json"
    if not path.exists():
        abort(404)
    data = _load_json(path)
    if index < 0 or index >= len(data["questions"]):
        abort(404)
    question = data["questions"][index]
    if not isinstance(question, dict):
        abort(404)
    return path, data, question


def _source_pdf(data: dict[str, Any], question: dict[str, Any]) -> Path:
    filename = str(data.get("source_pdf") or data.get("source_paper") or question.get("source_pdf") or "")
    path = SOURCE_DIR / Path(filename).name
    if not path.exists():
        abort(404, description=f"Source PDF not found: {filename}")
    return path


def _render_page(pdf_path: Path, page_number: int) -> Path:
    page_number = max(1, int(page_number))
    output_dir = PAGE_DIR / _safe_id(pdf_path.stem)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"page_{page_number}.png"
    if output_path.exists():
        return output_path
    with fitz.open(str(pdf_path)) as document:
        if page_number > len(document):
            abort(404, description=f"Page {page_number} does not exist in {pdf_path.name}")
        pixmap = document[page_number - 1].get_pixmap(dpi=150, alpha=False)
        pixmap.save(str(output_path))
    return output_path


@review_bp.route("/")
def dashboard():
    items = _items()
    stats = {status: sum(item["status"] == status for item in items) for status in ("PENDING", "APPROVED", "REJECTED", "NEEDS_REVIEW")}
    stats["CHAPTER_REVIEW"] = sum(item["chapter_missing"] and item["status"] not in {"APPROVED", "REJECTED"} for item in items)
    return render_template("extraction_review_dashboard.html", items=items, stats=stats)


@review_bp.route("/<path:item_id>", methods=["GET"])
def item(item_id: str):
    path, data, question = _find_item(item_id)
    source_pdf = _source_pdf(data, question)
    page_number = int(question.get("source_page") or question.get("page_number") or question.get("page") or 1)
    page_path = _render_page(source_pdf, page_number)
    items = _items()
    ids = [x["item_id"] for x in items]
    position = ids.index(item_id) if item_id in ids else 0
    previous_id = ids[position - 1] if position > 0 else None
    next_id = ids[position + 1] if position + 1 < len(ids) else None
    review = _load_review(item_id)
    values = _review_form_values(question, data)
    missing_inferred_fields = [name for name in INFERRED_FIELDS_REQUIRE_HUMAN_VERIFICATION if not str(values.get(name) or "").strip()]
    return render_template(
        "extraction_review_item.html",
        item_id=item_id,
        filename=path.name,
        data=data,
        question=question,
        values=values,
        review=review,
        missing_inferred_fields=missing_inferred_fields,
        source_pdf=source_pdf.name,
        page_number=page_number,
        page_url=url_for("extraction_review.page_image", item_id=item_id),
        previous_url=url_for("extraction_review.item", item_id=previous_id) if previous_id else None,
        next_url=url_for("extraction_review.item", item_id=next_id) if next_id else None,
        position=position + 1,
        total=len(ids),
    )


@review_bp.route("/<path:item_id>/review", methods=["POST"])
def review(item_id: str):
    _path, data, question = _find_item(item_id)
    status = request.form.get("status", "NEEDS_REVIEW").upper()
    if status not in {"APPROVED", "REJECTED", "NEEDS_REVIEW", "PENDING"}:
        return jsonify({"error": "Invalid review status"}), 400
    note = request.form.get("note", "").strip()
    current = _load_review(item_id)

    if status == "APPROVED":
        if current.get("status") == "APPROVED" and current.get("question_id"):
            return redirect(url_for("extraction_review.item", item_id=item_id))
        overrides: dict[str, Any] = {name: request.form.get(name, "") for name in (
            "question_text", "marks", "question_type", "answer_mode", "handwritten_upload_mode",
            "subject", "board", "class_level", "chapter", "topic", "subtopic", "difficulty",
            "competency", "correct_answer", "source_year", "diagram_reference",
        )}
        try:
            overrides["answer_choices"] = _parse_json_field(request.form.get("answer_choices", "[]"), "Answer choices", [])
            overrides["question_parts"] = _parse_json_field(request.form.get("question_parts", "[]"), "Question parts", [])
            overrides["assets"] = _parse_json_field(request.form.get("assets", "[]"), "Assets", [])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not overrides["question_text"].strip():
            return jsonify({"error": "Question text cannot be empty"}), 400
        if not overrides["chapter"].strip():
            return jsonify({"error": "Chapter must be verified before approval. Enter the chapter or choose Needs review."}), 400
        try:
            q = _question_from_extraction(question, data, overrides)
            storage.create_question(q)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        _save_review(item_id, "APPROVED", note or f"Imported as {q.question_id}", q.question_id)
    else:
        _save_review(item_id, status, note)
    return redirect(url_for("extraction_review.item", item_id=item_id))


@review_bp.route("/<path:item_id>/page.png")
def page_image(item_id: str):
    _path, data, question = _find_item(item_id)
    source_pdf = _source_pdf(data, question)
    page_number = int(question.get("source_page") or question.get("page_number") or question.get("page") or 1)
    path = _render_page(source_pdf, page_number)
    return send_file(path, mimetype="image/png", max_age=0)


def register_extraction_review(app):
    app.register_blueprint(review_bp)
