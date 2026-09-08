"""Extraction review package adapter.

The original MVP implementation remains in the sibling ``review_app.py`` module.
This package adapter keeps that implementation intact while allowing additive
review features, such as explicit OR-question splitting and visual-asset
refresh, to register cleanly.
"""
from __future__ import annotations

import html
import importlib.util
from pathlib import Path

from question_bank.extraction.question_asset_persistence import persist_source_visuals
from question_bank.extraction.or_question_splitter import split_or_parts

_LEGACY_PATH = Path(__file__).resolve().parents[1] / "review_app.py"
_SPEC = importlib.util.spec_from_file_location(
    "question_bank.extraction._legacy_review_app", _LEGACY_PATH
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load legacy extraction review module: {_LEGACY_PATH}")

_legacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_legacy)


def _source_review_form_values(q, data, review):
    """Return the immutable source/AI extraction view for the review page.

    Approval creates a separate canonical Question record. The review page must
    not replace the original AI extraction with the human-corrected canonical
    record after approval.
    """
    source_pdf = str(
        data.get("source_pdf") or data.get("source_paper") or q.get("source_pdf") or ""
    )
    field = _legacy._field
    values = {
        name: field(q, name)
        for name in (
            "answer_mode", "handwritten_upload_mode", "subject", "board",
            "class_level", "chapter", "topic", "subtopic", "difficulty",
            "competency", "source_year", "correct_answer", "diagram_reference",
        )
    }
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
        extraction_warnings=field(
            q, "extraction_warnings", default=data.get("extraction_warnings", [])
        ),
        question_type=str(field(q, "question_type", "type", default="saq")).lower(),
    )
    return values


# The legacy item view resolves its form values through its module-global
# function. Replace it so approved pages continue to show the original source
# extraction rather than the canonical edits.
_legacy._review_form_values = _source_review_form_values


_LEGACY_RENDER_TEMPLATE = _legacy.render_template


def _or_preview_html(values):
    """Build a pre-approval preview of the canonical questions an OR will create."""
    alternatives = split_or_parts(
        str(values.get("question_text") or ""), values.get("question_parts") or []
    )
    if len(alternatives) < 2:
        return ""

    cards = []
    for alternative in alternatives:
        identifier = html.escape(str(alternative.get("part_identifier") or "").upper())
        text = html.escape(str(alternative.get("question_text") or ""))
        marks = alternative.get("marks")
        marks_text = f" · {html.escape(str(marks))} marks" if marks not in (None, "") else ""
        visual = bool(alternative.get("diagram_reference") or alternative.get("assets"))
        visual_text = " · visual attached" if visual else ""
        cards.append(
            f'<div class="or-preview-card">'
            f'<div class="or-preview-title">Question {identifier}{marks_text}{visual_text}</div>'
            f'<div class="or-preview-text">{text}</div>'
            f'</div>'
        )

    return (
        '<div class="or-preview" id="or-preview">'
        '<strong>✓ Internal-choice OR detected</strong>'
        '<div class="or-preview-help">'
        'This question will be saved as separate canonical questions. '
        'Nothing is written to the question bank until you approve it.'
        '</div>'
        + "".join(cards)
        + '</div>'
    )


def _render_review_template(template_name, **context):
    rendered = _LEGACY_RENDER_TEMPLATE(template_name, **context)
    if template_name == "extraction_review_item.html":
        review = context.get("review") or {}
        if review.get("status") != "APPROVED":
            preview = _or_preview_html(context.get("values") or {})
            if preview:
                style = (
                    '<style>.or-preview{padding:12px;border:1px solid #9ec5fe;'
                    'background:#e7f1ff;border-radius:8px;margin:0 0 14px}.or-preview-help{'
                    'font-size:13px;color:#495057;margin:5px 0 10px}.or-preview-card{'
                    'background:#fff;border:1px solid #ced4da;border-radius:7px;padding:10px;'
                    'margin-top:8px}.or-preview-title{font-weight:700}.or-preview-text{'
                    'margin-top:5px;white-space:pre-wrap}</style>'
                )
                marker = '<h3>AI extraction + human verification</h3>'
                rendered = rendered.replace(marker, marker + style + preview, 1)
    return rendered


_legacy.render_template = _render_review_template

# Re-export the legacy module's implementation so existing imports keep working.
for _name in dir(_legacy):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_legacy, _name)

from question_bank.extraction.or_question_routes import register_or_question_review  # noqa: E402

_legacy_register = register_extraction_review


def _wrap_asset_refresh(app):
    """Refresh an already-stored single-question visual with the current detector.

    This repairs assets created by older detector versions when an approved item
    is opened. OR groups are deliberately skipped here because their alternatives
    may own different figures and require alternative-level association.
    """
    endpoint = "extraction_review.item"
    legacy_view = app.view_functions.get(endpoint)
    if legacy_view is None or getattr(legacy_view, "_asset_refresh", False):
        return

    def asset_refresh(item_id):
        try:
            _path, data, source_question = _legacy._find_item(item_id)
            review = _legacy._load_review(item_id)
            question_ids = review.get("question_ids") or []
            question_id = review.get("question_id")
            if review.get("status") == "APPROVED" and question_id and len(question_ids) <= 1:
                values = _legacy._review_form_values(source_question, data, review)
                refs = values.get("assets") or values.get("diagram_reference")
                if refs:
                    pages = _legacy._normalise_pages(source_question)
                    source_number = str(
                        _legacy._field(
                            source_question,
                            "source_question_number",
                            "question_number",
                            "number",
                            default="",
                        )
                    ).strip()
                    if pages and source_number:
                        persist_source_visuals(
                            _legacy._source_pdf(data, source_question),
                            int(pages[0]),
                            source_number,
                            str(question_id),
                        )
        except Exception:
            # The review page remains usable even if an asset refresh fails.
            pass
        return legacy_view(item_id)

    asset_refresh._asset_refresh = True
    app.view_functions[endpoint] = asset_refresh


def register_extraction_review(app):
    """Register the original review UI plus additive review features."""
    _legacy_register(app)
    _wrap_asset_refresh(app)
    register_or_question_review(app)
