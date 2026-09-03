"""Local human-verification interface for AI question extraction.

The interface deliberately keeps AI output separate from the canonical question
bank until a human approves it. Extraction JSON files are read from
EXTRACTION_INBOX_DIR (default: extraction_inbox). Review decisions are stored in
EXTRACTION_REVIEW_DIR (default: extraction_reviews).
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for

from exam_platform.models import ContentBlock, Question
from exam_platform.storage import storage

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


def _save_review(item_id: str, status: str, note: str = "") -> None:
    _review_path(item_id).write_text(
        json.dumps({"status": status, "updated_at": datetime.now().isoformat(), "note": note}, indent=2),
        encoding="utf-8",
    )


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
            result.append({
                "item_id": item_id,
                "file": path.name,
                "source_pdf": source_pdf,
                "index": index,
                "question_number": str(question.get("question_number") or question.get("number") or index + 1),
                "page_number": question.get("page_number") or question.get("page") or 1,
                "marks": question.get("marks"),
                "question_type": question.get("question_type") or question.get("type") or "",
                "status": review.get("status", "PENDING"),
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
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=150, alpha=False)
        pixmap.save(str(output_path))
    return output_path


def _next_question_id() -> str:
    numbers = [int(qid[1:]) for qid in storage.questions if qid.startswith("Q") and qid[1:].isdigit()]
    return f"Q{max(numbers, default=0) + 1:04d}"


def _question_text(question: dict[str, Any]) -> str:
    value = question.get("question_text")
    if value is None:
        value = question.get("text")
    if value is None:
        value = question.get("question")
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value or "").strip()


def _question_from_extraction(question: dict[str, Any], data: dict[str, Any], overrides: dict[str, Any]) -> Question:
    text_value = overrides.get("question_text", _question_text(question)).strip()
    choices = overrides.get("answer_choices")
    if choices is None:
        choices = question.get("answer_choices") or question.get("options") or []
    if not isinstance(choices, list):
        choices = []
    question_type = str(overrides.get("question_type") or question.get("question_type") or question.get("type") or "SAQ").lower()
    if question_type not in {"mcq", "vsaq", "saq", "laq"}:
        question_type = "saq"
    source_pdf = str(data.get("source_pdf") or data.get("source_paper") or "")
    year_match = re.search(r"(?:19|20)\d{2}", source_pdf)
    source_year = int(year_match.group()) if year_match else None
    marks_raw = overrides.get("marks", question.get("marks", 1))
    try:
        marks = float(marks_raw)
    except (TypeError, ValueError):
        marks = 1.0
    content = [ContentBlock("text", text_value)]
    diagram_reference = question.get("diagram_reference") or question.get("diagram")
    if diagram_reference:
        content.append(ContentBlock("image", str(diagram_reference), metadata={"source_reference": str(diagram_reference)}))
    return Question(
        question_id=_next_question_id(),
        question_type=question_type,
        answer_mode="option_selection" if question_type == "mcq" else "final_answer_selection_and_handwritten_upload",
        question_content=content,
        answer_choices=[str(x) for x in choices],
        correct_answer=overrides.get("correct_answer") or question.get("correct_answer"),
        marks=marks,
        handwritten_upload_mode="none",
        subject=str(overrides.get("subject") or question.get("subject") or "Mathematics"),
        board=str(overrides.get("board") or question.get("board") or "CBSE"),
        class_level=int(overrides.get("class_level") or question.get("class_level") or 12),
        chapter=overrides.get("chapter") or question.get("chapter"),
        topic=overrides.get("topic") or question.get("topic"),
        subtopic=overrides.get("subtopic") or question.get("subtopic"),
        difficulty=overrides.get("difficulty") or question.get("difficulty"),
        competency=overrides.get("competency") or question.get("competency"),
        source=source_pdf or None,
        source_year=source_year,
        status="active",
    )


@review_bp.route("/")
def dashboard():
    items = _items()
    stats = {status: sum(item["status"] == status for item in items) for status in ("PENDING", "APPROVED", "REJECTED", "NEEDS_REVIEW")}
    return render_template("extraction_review_dashboard.html", items=items, stats=stats)


@review_bp.route("/<path:item_id>", methods=["GET"])
def item(item_id: str):
    path, data, question = _find_item(item_id)
    source_pdf = _source_pdf(data, question)
    page_number = int(question.get("page_number") or question.get("page") or 1)
    page_path = _render_page(source_pdf, page_number)
    items = _items()
    ids = [x["item_id"] for x in items]
    position = ids.index(item_id) if item_id in ids else 0
    previous_id = ids[position - 1] if position > 0 else None
    next_id = ids[position + 1] if position + 1 < len(ids) else None
    review = _load_review(item_id)
    return render_template(
        "extraction_review_item.html",
        item_id=item_id,
        filename=path.name,
        data=data,
        question=question,
        review=review,
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
    if status == "APPROVED":
        overrides = {
            "question_text": request.form.get("question_text", ""),
            "marks": request.form.get("marks", ""),
            "question_type": request.form.get("question_type", ""),
            "subject": request.form.get("subject", ""),
            "board": request.form.get("board", ""),
            "class_level": request.form.get("class_level", ""),
            "chapter": request.form.get("chapter", ""),
            "topic": request.form.get("topic", ""),
            "competency": request.form.get("competency", ""),
            "difficulty": request.form.get("difficulty", ""),
            "correct_answer": request.form.get("correct_answer", ""),
        }
        q = _question_from_extraction(question, data, overrides)
        if not q.question_content[0].value:
            return jsonify({"error": "Question text cannot be empty"}), 400
        storage.create_question(q)
        _save_review(item_id, "APPROVED", note or f"Imported as {q.question_id}")
    else:
        _save_review(item_id, status, note)
    return redirect(url_for("extraction_review.item", item_id=item_id))


@review_bp.route("/<path:item_id>/page.png")
def page_image(item_id: str):
    _path, data, question = _find_item(item_id)
    source_pdf = _source_pdf(data, question)
    page_number = int(question.get("page_number") or question.get("page") or 1)
    path = _render_page(source_pdf, page_number)
    return send_file(path, mimetype="image/png", max_age=0)


def register_extraction_review(app):
    app.register_blueprint(review_bp)
