"""Routes used by the extraction review UI to verify persisted source visuals."""
from __future__ import annotations
import json
from pathlib import Path
from flask import Blueprint, jsonify, abort, send_file
from exam_platform.storage import storage
from question_bank.extraction.question_asset_persistence import persist_source_visuals

asset_review_bp = Blueprint("extraction_asset_review", __name__, url_prefix="/teacher/extraction-assets")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INBOX_DIR = PROJECT_ROOT / "extraction_inbox"
REVIEW_DIR = PROJECT_ROOT / "extraction_reviews"
SOURCE_DIR = PROJECT_ROOT / "source_pdfs"

def _load_review(item_id: str) -> dict:
    path = REVIEW_DIR / f"{item_id.replace(':','_')}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def _item(item_id: str):
    try:
        filename, raw_index = item_id.rsplit(":", 1)
        index = int(raw_index)
    except ValueError:
        abort(404)
    path = INBOX_DIR / f"{filename}.json"
    if not path.exists(): abort(404)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    question = data["questions"][index]
    return data, question

@asset_review_bp.route("/<path:item_id>")
def asset_status(item_id: str):
    review = _load_review(item_id)
    if review.get("status") != "APPROVED" or not review.get("question_id"):
        return jsonify({"status": "not_approved", "assets": []})
    data, question = _item(item_id)
    source_pdf_name = str(data.get("source_pdf") or data.get("source_paper") or question.get("source_pdf") or "")
    source_pdf = SOURCE_DIR / Path(source_pdf_name).name
    pages = question.get("source_pages") or [question.get("source_page") or question.get("page_number") or 1]
    page = int(pages[0])
    question_number = str(question.get("source_question_number") or question.get("question_number") or question.get("number") or "")
    rows = [dict(x) for x in storage.get_question_assets(review["question_id"])]
    if not rows:
        try:
            rows = persist_source_visuals(source_pdf, page, question_number, str(review["question_id"]))
        except Exception as exc:
            return jsonify({"status": "error", "error": str(exc), "assets": []}), 500
    assets = []
    for row in rows:
        asset_id = str(row.get("asset_id"))
        assets.append({"asset_id": asset_id, "asset_type": row.get("asset_type"), "url": f"/teacher/extraction-assets/{item_id}/{asset_id}.png"})
    return jsonify({"status": "stored" if assets else "no_visual_detected", "assets": assets})

@asset_review_bp.route("/<path:item_id>/<asset_id>.png")
def asset_image(item_id: str, asset_id: str):
    review = _load_review(item_id)
    if review.get("status") != "APPROVED" or not review.get("question_id"): abort(404)
    row = next((dict(x) for x in storage.get_question_assets(review["question_id"]) if str(x.get("asset_id")) == asset_id), None)
    if not row: abort(404)
    path = Path(str(row.get("file_path") or ""))
    if not path.exists(): abort(404, description="Stored visual asset file is missing")
    return send_file(path, mimetype="image/png", max_age=0)

def register_asset_review(app):
    app.register_blueprint(asset_review_bp)
