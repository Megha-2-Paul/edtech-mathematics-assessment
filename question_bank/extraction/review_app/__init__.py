"""Extraction review package adapter."""
from __future__ import annotations

import html
import importlib.util
import re
from pathlib import Path

import fitz
from flask import request, send_file, url_for

from exam_platform.storage import storage
from question_bank.extraction.question_asset_persistence import (
    _best_visual_rect,
    _graphic_candidates,
    persist_source_visuals,
)
from question_bank.extraction.page_renderer import render_region
from question_bank.extraction.question_boundary import detect_question_boundaries
from question_bank.extraction.or_question_splitter import split_or_parts

_LEGACY_PATH = Path(__file__).resolve().parents[1] / "review_app.py"
_SPEC = importlib.util.spec_from_file_location("question_bank.extraction._legacy_review_app", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load legacy extraction review module: {_LEGACY_PATH}")
_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)


def _source_review_form_values(q, data, review):
    """Keep the original AI/source extraction immutable after approval."""
    source_pdf = str(data.get("source_pdf") or data.get("source_paper") or q.get("source_pdf") or "")
    field = _legacy._field
    values = {name: field(q, name) for name in (
        "answer_mode", "handwritten_upload_mode", "subject", "board", "class_level",
        "chapter", "topic", "subtopic", "difficulty", "competency", "source_year",
        "correct_answer", "diagram_reference",
    )}
    values.update(
        question_text=_legacy._question_text(q),
        answer_choices=field(q, "answer_choices", "options", default=[]),
        question_parts=field(q, "question_parts", default=[]),
        source=field(q, "source", default=source_pdf),
        source_pdf=source_pdf,
        source_page=field(q, "source_page", "page_number", "page"),
        source_pages=_legacy._normalise_pages(q),
        source_question_number=field(q, "source_question_number", "question_number", "number"),
        source_occurrence_id=field(q, "source_occurrence_id"),
        assets=field(q, "assets", default=[]),
        extraction_provider=field(q, "extraction_provider", default=data.get("extraction_provider")),
        extraction_model=field(q, "extraction_model", default=data.get("extraction_model")),
        extraction_run_id=field(q, "extraction_run_id", default=data.get("extraction_run_id")),
        extraction_confidence=field(q, "extraction_confidence", default=data.get("extraction_confidence")),
        extraction_warnings=field(q, "extraction_warnings", default=data.get("extraction_warnings", [])),
        question_type=str(field(q, "question_type", "type", default="saq")).lower(),
    )
    return values


_legacy._review_form_values = _source_review_form_values
_LEGACY_RENDER_TEMPLATE = _legacy.render_template


def _canonical_question_ids(review):
    ids = review.get("question_ids") or []
    if isinstance(ids, str):
        ids = [ids]
    if not ids and review.get("question_id"):
        ids = [review["question_id"]]
    return [str(x) for x in ids if x]


def _question_text_from_canonical(question):
    blocks = [b for b in (question.question_content or []) if getattr(b, "type", "") == "text"]
    return str(blocks[0].value or "") if blocks else ""


def _part_identifier_from_canonical(question):
    text = _question_text_from_canonical(question)
    match = re.match(r"\s*\(([a-z])\)\s*", text, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _student_preview_visual_path(item_id, source_question, data, part_identifier=None):
    """Render a temporary source visual, optionally scoped to an OR part."""
    try:
        pdf_path = _legacy._source_pdf(data, source_question)
        pages = _legacy._normalise_pages(source_question)
        question_number = str(_legacy._field(source_question, "source_question_number", "question_number", "number", default="")).strip()
        if not pages or not question_number:
            return None
        output_dir = _legacy.REVIEW_DIR / "student_preview_visuals"
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_{str(part_identifier).strip().lower()}" if part_identifier else ""
        output_path = output_dir / f"{_legacy._safe_id(item_id)}{suffix}.png"
        with fitz.open(str(pdf_path)) as document:
            page_number = int(pages[0])
            if page_number < 1 or page_number > len(document):
                return None
            page = document[page_number - 1]
            boundary = next((b for b in detect_question_boundaries(page, page_number) if str(b.question_number) == question_number), None)
            if boundary is None:
                return None
            region = fitz.Rect(boundary.bbox) & page.rect
            candidates = _graphic_candidates(page, page_number, region)
            rect = _best_visual_rect(page, candidates, region, part_identifier=part_identifier)
            if rect is None or rect.get_area() <= 0:
                return None
            rect = fitz.Rect(max(region.x0, rect.x0 - 12), max(region.y0, rect.y0 - 12), min(region.x1, rect.x1 + 12), min(region.y1, rect.y1 + 12))
            render_region(page, tuple(rect), output_path, dpi=220)
        return output_path if output_path.exists() else None
    except Exception:
        return None


def _or_preview_html(values, item_id=None, source_question=None, data=None):
    alternatives = split_or_parts(str(values.get("question_text") or ""), values.get("question_parts") or [])
    if len(alternatives) < 2:
        return ""
    cards = []
    for alternative in alternatives:
        identifier = str(alternative.get("part_identifier") or "").lower()
        text = html.escape(str(alternative.get("question_text") or ""))
        marks = alternative.get("marks")
        marks_text = f'<div class="student-preview-marks">{html.escape(str(marks))} marks</div>' if marks not in (None, "") else ""
        image_html = ""
        if item_id and source_question is not None and data is not None:
            path = _student_preview_visual_path(item_id, source_question, data, identifier)
            if path:
                image_url = url_for("extraction_review.student_preview_visual", item_id=item_id, part=identifier)
                image_html = f'<div class="student-preview-visual"><img src="{html.escape(image_url)}" alt="Question {html.escape(identifier.upper())} visual"></div>'
        cards.append(
            f'<div class="or-preview-card"><div class="or-preview-title">Question {html.escape(identifier.upper())}</div>'
            f'<div class="or-preview-text">{text}</div>{marks_text}{image_html}</div>'
        )
    return (
        '<div class="or-preview" id="or-preview"><strong>✓ Internal-choice OR detected</strong>'
        '<div class="or-preview-help">The student version will be saved as two separate canonical questions. Nothing is written to the question bank until approval.</div>'
        + '<div class="or-preview-separator">OR</div>'.join(cards) + '</div>'
    )


def _render_review_template(template_name, **context):
    rendered = _LEGACY_RENDER_TEMPLATE(template_name, **context)
    if template_name == "extraction_review_item.html" and (context.get("review") or {}).get("status") != "APPROVED":
        values = context.get("values") or {}
        preview = _or_preview_html(values, context.get("item_id"), context.get("question"), context.get("data"))
        if preview:
            style = '<style>.or-preview{padding:12px;border:1px solid #9ec5fe;background:#e7f1ff;border-radius:8px;margin:0 0 14px}.or-preview-help{font-size:13px;color:#495057;margin:5px 0 10px}.or-preview-card{background:#fff;border:1px solid #ced4da;border-radius:7px;padding:10px;margin-top:8px}.or-preview-title{font-weight:700}.or-preview-text{margin-top:5px;white-space:pre-wrap}.or-preview-separator{font-weight:800;text-align:center;padding:8px 0;color:#495057}.student-preview-marks{font-size:12px;color:#666;margin-top:8px}.student-preview-visual{margin-top:14px;text-align:center}.student-preview-visual img{max-width:100%;max-height:320px;border:1px solid #ddd;border-radius:6px;background:#fff}</style>'
            marker = '<h3>AI extraction + human verification</h3>'
            rendered = rendered.replace(marker, marker + style + preview, 1)
    return rendered


_legacy.render_template = _render_review_template


def _canonical_preview_html(item_id, review):
    ids = _canonical_question_ids(review)
    questions = [storage.get_question(qid) for qid in ids]
    questions = [q for q in questions if q is not None]
    if not questions:
        return ""
    cards = []
    for index, question in enumerate(questions):
        text = _question_text_from_canonical(question)
        identifier = _part_identifier_from_canonical(question)
        label = f"Question {identifier.upper()}" if identifier else f"Question {index + 1}"
        choices = list(question.answer_choices or [])
        choices_html = '<div class="student-preview-choices">' + "".join(f'<div>{html.escape(str(choice))}</div>' for choice in choices) + '</div>' if choices else ""
        try:
            assets = [dict(x) for x in storage.get_question_assets(question.question_id)]
        except Exception:
            assets = []
        asset_html = "".join(
            f'<div class="student-preview-visual"><img src="{html.escape(url_for("extraction_review.student_preview_asset", item_id=item_id, asset_id=str(a.get("asset_id"))))}" alt="{html.escape(label)} visual"></div>'
            for a in assets if a.get("asset_id")
        )
        marks = f'<div class="student-preview-marks">{html.escape(str(question.marks))} marks</div>' if question.marks is not None else ""
        cards.append(f'<div class="student-preview-paper"><div class="student-preview-question-label">{html.escape(label)}</div><div class="student-preview-question">{html.escape(text).replace(chr(10), "<br>")}</div>{marks}{choices_html}{asset_html}</div>')
    body = '<div class="student-preview-or">OR</div>'.join(cards) if len(cards) == 2 else ''.join(cards)
    return '<div class="student-preview" id="student-preview"><div class="student-preview-heading">Live student preview — approved canonical version</div><div class="student-preview-note">This preview uses the saved canonical Question record(s), so human corrections are reflected here. The AI extraction above remains unchanged for audit.</div>' + body + '</div>'


def _source_preview_html(item_id, source_question, data, values):
    alternatives = split_or_parts(str(values.get("question_text") or ""), values.get("question_parts") or [])
    if len(alternatives) == 2:
        return _or_preview_html(values, item_id, source_question, data)
    text = html.escape(str(values.get("question_text") or ""))
    choices = values.get("answer_choices") or []
    choices_html = '<div class="student-preview-choices">' + "".join(f'<div>{html.escape(str(choice))}</div>' for choice in choices) + '</div>' if choices else ""
    path = _student_preview_visual_path(item_id, source_question, data)
    image_html = ""
    if path:
        image_html = f'<div class="student-preview-visual"><img src="{html.escape(url_for("extraction_review.student_preview_visual", item_id=item_id))}" alt="Question visual"></div>'
    return '<div class="student-preview" id="student-preview"><div class="student-preview-heading">Live student preview</div><div class="student-preview-note">This is an approximation of how the question will be presented to a student. The source PDF remains the verification ground truth.</div><div class="student-preview-paper"><div class="student-preview-question">' + text.replace(chr(10), "<br>") + '</div>' + choices_html + image_html + '</div></div>'


def _inject_student_preview(rendered, item_id, source_question, data, values, review):
    preview = _canonical_preview_html(item_id, review) if review.get("status") == "APPROVED" else _source_preview_html(item_id, source_question, data, values)
    rendered = rendered.replace("The fields below are loaded from the canonical question that was approved. The original AI extraction remains preserved separately for audit.", "This page continues to show the original AI extraction and source for audit. Human corrections are stored in the approved canonical question record(s).")
    if not preview:
        return rendered
    style = '<style>.student-preview{margin-bottom:16px;padding:14px;border:1px solid #b7c9e8;background:#f4f8ff;border-radius:10px}.student-preview-heading{font-size:18px;font-weight:700;margin-bottom:4px}.student-preview-note{font-size:12px;color:#666;margin-bottom:10px}.student-preview-paper{background:#fff;border:1px solid #d7dce2;border-radius:8px;padding:16px}.student-preview-paper+.student-preview-paper{margin-top:8px}.student-preview-question-label{font-weight:700;font-size:14px;margin-bottom:5px}.student-preview-question{font-size:17px;line-height:1.6}.student-preview-marks{font-size:12px;color:#666;margin-top:8px}.student-preview-choices{margin-top:10px;display:grid;gap:6px}.student-preview-choices div{padding:7px 9px;border:1px solid #e3e6ea;border-radius:6px}.student-preview-or{font-weight:800;text-align:center;padding:8px 0;color:#495057}.student-preview-visual{margin-top:14px;text-align:center}.student-preview-visual img{max-width:100%;max-height:320px;border:1px solid #ddd;border-radius:6px;background:#fff}</style>'
    marker = '<h3>AI extraction + human verification</h3>'
    return rendered.replace(marker, style + preview + marker, 1)


def _dashboard_view():
    items = []
    for p in _legacy._extraction_files():
        try:
            data = _legacy._load_json(p)
        except ValueError:
            continue
        source_pdf = str(data.get("source_pdf") or data.get("source_paper") or "")
        for index, q in enumerate(data["questions"]):
            if not isinstance(q, dict):
                continue
            item_id = f"{p.stem}:{index}"
            review = _legacy._load_review(item_id)
            values = _source_review_form_values(q, data, review)
            ids = _canonical_question_ids(review)
            canonical = storage.get_question(ids[0]) if ids else None
            if canonical:
                for name in ("class_level", "board", "chapter", "topic", "difficulty", "source_year", "marks", "question_type"):
                    if hasattr(canonical, name):
                        values[name] = getattr(canonical, name)
            source_year = values.get("source_year") or _legacy._source_year(source_pdf)
            items.append({"item_id": item_id, "file": p.name, "source_pdf": source_pdf, "index": index, "question_number": str(values.get("source_question_number") or index + 1), "page_number": values.get("source_page") or 1, "marks": values.get("marks"), "question_type": values.get("question_type") or "", "status": review.get("status", "PENDING"), "chapter_missing": not str(values.get("chapter") or "").strip(), "class_level": values.get("class_level"), "board": values.get("board"), "source_year": source_year, "chapter": values.get("chapter"), "topic": values.get("topic"), "difficulty": values.get("difficulty")})
    stats = {s: sum(x["status"] == s for x in items) for s in ("PENDING", "APPROVED", "REJECTED", "NEEDS_REVIEW")}
    stats["CHAPTER_REVIEW"] = sum(x["chapter_missing"] and x["status"] not in {"APPROVED", "REJECTED"} for x in items)
    return _LEGACY_RENDER_TEMPLATE("extraction_review_dashboard.html", items=items, stats=stats)


_legacy_item_view = None


def _asset_refresh_view(item_id):
    """Refresh approved visuals; OR children are refreshed against their own part."""
    try:
        _path, data, source_question = _legacy._find_item(item_id)
        review = _legacy._load_review(item_id)
        ids = _canonical_question_ids(review)
        pages = _legacy._normalise_pages(source_question)
        source_number = str(_legacy._field(source_question, "source_question_number", "question_number", "number", default="")).strip()
        if review.get("status") == "APPROVED" and ids and pages and source_number:
            for qid in ids:
                question = storage.get_question(qid)
                if not question:
                    continue
                identifier = _part_identifier_from_canonical(question)
                if len(ids) > 1 and identifier:
                    refreshed = persist_source_visuals(_legacy._source_pdf(data, source_question), int(pages[0]), source_number, qid, part_identifier=identifier)
                    if not refreshed:
                        storage.delete_question_assets(qid)
                elif len(ids) == 1:
                    values = _source_review_form_values(source_question, data, review)
                    if values.get("assets") or values.get("diagram_reference"):
                        persist_source_visuals(_legacy._source_pdf(data, source_question), int(pages[0]), source_number, qid)
    except Exception:
        pass
    rendered = _legacy_item_view(item_id)
    try:
        _path, data, source_question = _legacy._find_item(item_id)
        review = _legacy._load_review(item_id)
        values = _legacy._review_form_values(source_question, data, review)
        rendered = _inject_student_preview(rendered, item_id, source_question, data, values, review)
    except Exception:
        pass
    return rendered


def _student_preview_asset(item_id, asset_id):
    try:
        review = _legacy._load_review(item_id)
        ids = _canonical_question_ids(review)
        if review.get("status") != "APPROVED" or not ids:
            return ("Asset preview not available.", 404)
        for qid in ids:
            for asset in storage.get_question_assets(qid):
                if str(asset.get("asset_id")) == str(asset_id):
                    path = Path(str(asset.get("file_path") or ""))
                    if path.exists() and path.is_file():
                        return send_file(path, mimetype="image/png", max_age=0)
    except Exception:
        pass
    return ("Asset preview not available.", 404)


def _student_preview_visual(item_id):
    _path, data, source_question = _legacy._find_item(item_id)
    part_identifier = str(request.args.get("part") or "").strip().lower() or None
    path = _student_preview_visual_path(item_id, source_question, data, part_identifier)
    if path is None:
        return ("Visual preview not available for this question.", 404)
    return send_file(path, mimetype="image/png", max_age=0)


for _name in dir(_legacy):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_legacy, _name)

from question_bank.extraction.or_question_routes import register_or_question_review  # noqa: E402

_legacy_register = register_extraction_review


def register_extraction_review(app):
    _legacy_register(app)
    global _legacy_item_view
    _legacy_item_view = app.view_functions.get("extraction_review.item")
    if _legacy_item_view is not None:
        app.view_functions["extraction_review.item"] = _asset_refresh_view
    app.view_functions["extraction_review.dashboard"] = _dashboard_view
    app.add_url_rule("/teacher/extraction-review/<path:item_id>/student-preview-visual", endpoint="extraction_review.student_preview_visual", view_func=_student_preview_visual)
    app.add_url_rule("/teacher/extraction-review/<path:item_id>/student-preview-asset/<asset_id>", endpoint="extraction_review.student_preview_asset", view_func=_student_preview_asset)
    register_or_question_review(app)
