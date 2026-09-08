"""Extraction review package adapter.

The original MVP implementation remains in the sibling ``review_app.py`` module.
This package adapter keeps that implementation intact while allowing additive
review features, such as explicit OR-question splitting, visual refresh, and a
student-facing preview, to register cleanly.
"""
from __future__ import annotations

import html
import importlib.util
from pathlib import Path

import fitz
from flask import send_file, url_for

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
    """Return the immutable source/AI extraction view for the review page."""
    source_pdf = str(data.get("source_pdf") or data.get("source_paper") or q.get("source_pdf") or "")
    field = _legacy._field
    values = {name: field(q, name) for name in ("answer_mode", "handwritten_upload_mode", "subject", "board", "class_level", "chapter", "topic", "subtopic", "difficulty", "competency", "source_year", "correct_answer", "diagram_reference")}
    values.update(
        question_text=_legacy._question_text(q), answer_choices=field(q, "answer_choices", "options", default=[]),
        question_parts=field(q, "question_parts", default=[]), source=field(q, "source", default=source_pdf),
        source_pdf=source_pdf, source_page=field(q, "source_page", "page_number", "page"), source_pages=_legacy._normalise_pages(q),
        source_question_number=field(q, "source_question_number", "question_number", "number"), source_occurrence_id=field(q, "source_occurrence_id"),
        assets=field(q, "assets", default=[]), extraction_provider=field(q, "extraction_provider", default=data.get("extraction_provider")),
        extraction_model=field(q, "extraction_model", default=data.get("extraction_model")), extraction_run_id=field(q, "extraction_run_id", default=data.get("extraction_run_id")),
        extraction_confidence=field(q, "extraction_confidence", default=data.get("extraction_confidence")), extraction_warnings=field(q, "extraction_warnings", default=data.get("extraction_warnings", [])),
        question_type=str(field(q, "question_type", "type", default="saq")).lower(),
    )
    return values


_legacy._review_form_values = _source_review_form_values
_LEGACY_RENDER_TEMPLATE = _legacy.render_template


def _or_preview_html(values):
    """Show the proposed OR split before approval without changing the source fields."""
    alternatives = split_or_parts(str(values.get("question_text") or ""), values.get("question_parts") or [])
    if len(alternatives) < 2:
        return ""
    cards = []
    for alternative in alternatives:
        identifier = html.escape(str(alternative.get("part_identifier") or "").upper())
        text = html.escape(str(alternative.get("question_text") or ""))
        marks = alternative.get("marks")
        marks_text = f" · {html.escape(str(marks))} marks" if marks not in (None, "") else ""
        visual_text = " · visual attached" if (alternative.get("diagram_reference") or alternative.get("assets")) else ""
        cards.append(f'<div class="or-preview-card"><div class="or-preview-title">Question {identifier}{marks_text}{visual_text}</div><div class="or-preview-text">{text}</div></div>')
    return '<div class="or-preview" id="or-preview"><strong>✓ Internal-choice OR detected</strong><div class="or-preview-help">This question will be saved as separate canonical questions. Nothing is written to the question bank until you approve it.</div>' + "<div class=\"or-preview-separator\">OR</div>".join([cards[0], cards[1]]) + '</div>'


def _render_review_template(template_name, **context):
    rendered = _LEGACY_RENDER_TEMPLATE(template_name, **context)
    if template_name == "extraction_review_item.html":
        review = context.get("review") or {}
        if review.get("status") != "APPROVED":
            preview = _or_preview_html(context.get("values") or {})
            if preview:
                style = '<style>.or-preview{padding:12px;border:1px solid #9ec5fe;background:#e7f1ff;border-radius:8px;margin:0 0 14px}.or-preview-help{font-size:13px;color:#495057;margin:5px 0 10px}.or-preview-card{background:#fff;border:1px solid #ced4da;border-radius:7px;padding:10px;margin-top:8px}.or-preview-title{font-weight:700}.or-preview-text{margin-top:5px;white-space:pre-wrap}.or-preview-separator{font-weight:800;text-align:center;padding:8px 0;color:#495057}</style>'
                marker = '<h3>AI extraction + human verification</h3>'
                rendered = rendered.replace(marker, marker + style + preview, 1)
    return rendered


_legacy.render_template = _render_review_template


def _canonical_question_ids(review):
    """Return all canonical question IDs created by approval, in source order."""
    ids = review.get("question_ids") or []
    if isinstance(ids, str):
        ids = [ids]
    if not ids and review.get("question_id"):
        ids = [review["question_id"]]
    return [str(x) for x in ids if x]


def _question_text_from_canonical(question):
    blocks = [b for b in (question.question_content or []) if getattr(b, "type", "") == "text"]
    return str(blocks[0].value or "") if blocks else ""


def _canonical_preview_item(question, index, total):
    """Build the minimal display data needed for a student-facing preview."""
    text = _question_text_from_canonical(question)
    label = f"Question {text[:4].strip()}" if text.startswith("(") else f"Question {index + 1}"
    if total > 1 and text.startswith("("):
        label = f"Question {text[1:2].upper()}"
    assets = []
    try:
        assets = [dict(x) for x in _legacy.storage.get_question_assets(question.question_id)]
    except Exception:
        assets = []
    return {
        "question_id": question.question_id,
        "label": label,
        "text": text,
        "choices": list(question.answer_choices or []),
        "assets": assets,
        "marks": question.marks,
    }


def _canonical_preview_html(item_id, review):
    question_ids = _canonical_question_ids(review)
    questions = [q for q in ([_legacy.storage.get_question(qid) for qid in question_ids]) if q is not None]
    if not questions:
        return ""
    items = [_canonical_preview_item(q, i, len(questions)) for i, q in enumerate(questions)]
    cards = []
    for item in items:
        text = html.escape(item["text"])
        choices = item["choices"]
        choices_html = '<div class="student-preview-choices">' + "".join(f'<div>{html.escape(str(choice))}</div>' for choice in choices) + '</div>' if choices else ""
        asset_html = ""
        for asset in item["assets"]:
            asset_id = str(asset.get("asset_id") or "")
            if not asset_id:
                continue
            image_url = url_for("extraction_review.student_preview_asset", item_id=item_id, asset_id=asset_id)
            asset_html += f'<div class="student-preview-visual"><img src="{html.escape(image_url)}" alt="Question visual"></div>'
        marks = f'<div class="student-preview-marks">{html.escape(str(item["marks"]))} marks</div>' if item["marks"] is not None else ""
        cards.append(f'<div class="student-preview-paper"><div class="student-preview-question-label">{html.escape(item["label"])}</div><div class="student-preview-question">{text.replace(chr(10), "<br>")}</div>{marks}{choices_html}{asset_html}</div>')
    separator = '<div class="student-preview-or">OR</div>' if len(cards) == 2 else ""
    body = separator.join(cards)
    return '<div class="student-preview" id="student-preview"><div class="student-preview-heading">Live student preview — approved canonical version</div><div class="student-preview-note">This preview uses the saved canonical Question record(s), so human corrections are reflected here. The AI extraction above remains unchanged for audit.</div>' + body + '</div>'


def _source_preview_html(item_id, source_question, data, values):
    """Render a pre-approval preview, splitting explicit OR alternatives visually."""
    alternatives = split_or_parts(str(values.get("question_text") or ""), values.get("question_parts") or [])
    if len(alternatives) == 2:
        cards = []
        for alternative in alternatives:
            identifier = html.escape(str(alternative.get("part_identifier") or "").upper())
            text = html.escape(str(alternative.get("question_text") or ""))
            choices = alternative.get("answer_choices") or []
            choices_html = '<div class="student-preview-choices">' + "".join(f'<div>{html.escape(str(choice))}</div>' for choice in choices) + '</div>' if choices else ""
            cards.append(f'<div class="student-preview-paper"><div class="student-preview-question-label">Question {identifier}</div><div class="student-preview-question">{text.replace(chr(10), "<br>")}</div>{choices_html}</div>')
        body = '<div class="student-preview-or">OR</div>'.join(cards)
        return '<div class="student-preview" id="student-preview"><div class="student-preview-heading">Live student preview — proposed OR split</div><div class="student-preview-note">This is the student layout that will be created if you approve this extraction. The original AI extraction remains unchanged above.</div>' + body + '</div>'

    visual_path = _student_preview_visual_path(item_id, source_question, data)
    text = html.escape(str(values.get("question_text") or ""))
    choices = values.get("answer_choices") or []
    choices_html = '<div class="student-preview-choices">' + "".join(f'<div>{html.escape(str(choice))}</div>' for choice in choices) + '</div>' if choices else ""
    image_html = ""
    if visual_path:
        image_url = url_for("extraction_review.student_preview_visual", item_id=item_id)
        image_html = f'<div class="student-preview-visual"><img src="{html.escape(image_url)}" alt="Question diagram preview"></div>'
    return '<div class="student-preview" id="student-preview"><div class="student-preview-heading">Live student preview</div><div class="student-preview-note">This is an approximation of how the question will be presented to a student. The source PDF remains the verification ground truth.</div><div class="student-preview-paper"><div class="student-preview-question">' + text.replace(chr(10), "<br>") + '</div>' + choices_html + image_html + '</div></div>'


def _inject_student_preview(rendered, item_id, source_question, data, values, review):
    if review.get("status") == "APPROVED":
        preview = _canonical_preview_html(item_id, review)
    else:
        preview = _source_preview_html(item_id, source_question, data, values)
    rendered = rendered.replace("The fields below are loaded from the canonical question that was approved. The original AI extraction remains preserved separately for audit.", "This page continues to show the original AI extraction and source for audit. Human corrections are stored in the approved canonical question record(s).")
    if not preview:
        return rendered
    style = '<style>.student-preview{margin-bottom:16px;padding:14px;border:1px solid #b7c9e8;background:#f4f8ff;border-radius:10px}.student-preview-heading{font-size:18px;font-weight:700;margin-bottom:4px}.student-preview-note{font-size:12px;color:#666;margin-bottom:10px}.student-preview-paper{background:#fff;border:1px solid #d7dce2;border-radius:8px;padding:16px}.student-preview-paper+.student-preview-paper{margin-top:8px}.student-preview-question-label{font-weight:700;font-size:14px;margin-bottom:5px}.student-preview-question{font-size:17px;line-height:1.6}.student-preview-marks{font-size:12px;color:#666;margin-top:8px}.student-preview-choices{margin-top:10px;display:grid;gap:6px}.student-preview-choices div{padding:7px 9px;border:1px solid #e3e6ea;border-radius:6px}.student-preview-or{font-weight:800;text-align:center;padding:8px 0;color:#495057}.student-preview-visual{margin-top:14px;text-align:center}.student-preview-visual img{max-width:100%;max-height:320px;border:1px solid #ddd;border-radius:6px;background:#fff}</style>'
    marker = '<h3>AI extraction + human verification</h3>'
    return rendered.replace(marker, style + preview + marker, 1)


def _dashboard_view():
    """Render the dashboard with useful extraction metadata and canonical values when approved."""
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
            question_ids = _canonical_question_ids(review)
            canonical = _legacy.storage.get_question(question_ids[0]) if question_ids else None
            if canonical:
                for name in ("class_level", "board", "chapter", "topic", "difficulty", "source_year", "marks", "question_type"):
                    if hasattr(canonical, name):
                        values[name] = getattr(canonical, name)
            source_year = values.get("source_year") or _legacy._source_year(source_pdf)
            items.append({"item_id": item_id, "file": p.name, "source_pdf": source_pdf, "index": index, "question_number": str(values.get("source_question_number") or index + 1), "page_number": values.get("source_page") or 1, "marks": values.get("marks"), "question_type": values.get("question_type") or "", "status": review.get("status", "PENDING"), "chapter_missing": not str(values.get("chapter") or "").strip(), "class_level": values.get("class_level"), "board": values.get("board"), "source_year": source_year, "chapter": values.get("chapter"), "topic": values.get("topic"), "difficulty": values.get("difficulty")})
    stats = {s: sum(x["status"] == s for x in items) for s in ("PENDING", "APPROVED", "REJECTED", "NEEDS_REVIEW")}
    stats["CHAPTER_REVIEW"] = sum(x["chapter_missing"] and x["status"] not in {"APPROVED", "REJECTED"} for x in items)
    return _LEGACY_RENDER_TEMPLATE("extraction_review_dashboard.html", items=items, stats=stats)


def _student_preview_visual_path(item_id, source_question, data):
    """Render a non-persistent visual crop for the pre-approval student preview."""
    try:
        pdf_path = _legacy._source_pdf(data, source_question)
        pages = _legacy._normalise_pages(source_question)
        question_number = str(_legacy._field(source_question, "source_question_number", "question_number", "number", default="")).strip()
        if not pages or not question_number:
            return None
        output_dir = _legacy.REVIEW_DIR / "student_preview_visuals"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{_legacy._safe_id(item_id)}.png"
        with fitz.open(str(pdf_path)) as document:
            page_number = int(pages[0])
            if page_number < 1 or page_number > len(document):
                return None
            page = document[page_number - 1]
            boundaries = detect_question_boundaries(page, page_number)
            boundary = next((b for b in boundaries if str(b.question_number) == question_number), None)
            if boundary is None:
                return None
            region = fitz.Rect(boundary.bbox) & page.rect
            candidates = _graphic_candidates(page, page_number, region)
            rect = _best_visual_rect(page, candidates, region)
            if rect is None or rect.get_area() <= 0:
                return None
            rect = fitz.Rect(max(region.x0, rect.x0 - 12), max(region.y0, rect.y0 - 12), min(region.x1, rect.x1 + 12), min(region.y1, rect.y1 + 12))
            render_region(page, tuple(rect), output_path, dpi=220)
        return output_path if output_path.exists() else None
    except Exception:
        return None


def _student_preview_asset(item_id, asset_id):
    """Serve an already-persisted canonical question asset after checking ownership."""
    try:
        review = _legacy._load_review(item_id)
        question_ids = _canonical_question_ids(review)
        if review.get("status") != "APPROVED" or not question_ids:
            return ("Asset preview not available.", 404)
        for question_id in question_ids:
            for asset in _legacy.storage.get_question_assets(question_id):
                if str(asset.get("asset_id")) == str(asset_id):
                    path = Path(str(asset.get("file_path") or ""))
                    if path.exists() and path.is_file():
                        return send_file(path)
    except Exception:
        pass
    return ("Asset preview not available.", 404)


def _student_preview_visual(item_id):
    _path, data, source_question = _legacy._find_item(item_id)
    path = _student_preview_visual_path(item_id, source_question, data)
    if path is None:
        return ("Visual preview not available for this question.", 404)
    return send_file(path, mimetype="image/png")


for _name in dir(_legacy):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_legacy, _name)

from question_bank.extraction.or_question_routes import register_or_question_review  # noqa: E402

_legacy_register = register_extraction_review


def register_extraction_review(app):
    """Register the original review UI plus additive review features."""
    _legacy_register(app)
    global _legacy_item_view
    _legacy_item_view = app.view_functions.get("extraction_review.item")
    if _legacy_item_view is not None:
        app.view_functions["extraction_review.item"] = _asset_refresh_view
    app.view_functions["extraction_review.dashboard"] = _dashboard_view
    app.add_url_rule("/teacher/extraction-review/<path:item_id>/student-preview-visual", endpoint="extraction_review.student_preview_visual", view_func=_student_preview_visual)
    app.add_url_rule("/teacher/extraction-review/<path:item_id>/student-preview-asset/<asset_id>", endpoint="extraction_review.student_preview_asset", view_func=_student_preview_asset)
    register_or_question_review(app)


_legacy_item_view = None


def _asset_refresh_view(item_id):
    """Refresh approved assets and add the live student preview to every review page."""
    try:
        _path, data, source_question = _legacy._find_item(item_id)
        review = _legacy._load_review(item_id)
        question_ids = _canonical_question_ids(review)
        if review.get("status") == "APPROVED" and len(question_ids) == 1:
            values = _legacy._review_form_values(source_question, data, review)
            refs = values.get("assets") or values.get("diagram_reference")
            if refs:
                pages = _legacy._normalise_pages(source_question)
                source_number = str(_legacy._field(source_question, "source_question_number", "question_number", "number", default="")).strip()
                if pages and source_number:
                    persist_source_visuals(_legacy._source_pdf(data, source_question), int(pages[0]), source_number, str(question_ids[0]))
    except Exception:
        pass
    rendered = _legacy_item_view(item_id)
    try:
        _path, data, source_question = _legacy._find_item(item_id)
        review = _legacy._load_review(item_id)
        values = _source_review_form_values(source_question, data, review)
        rendered = _inject_student_preview(rendered, item_id, source_question, data, values, review)
    except Exception:
        pass
    return rendered
