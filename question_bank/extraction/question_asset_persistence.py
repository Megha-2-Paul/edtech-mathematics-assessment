"""Persist source-PDF visual assets for approved canonical questions."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from exam_platform.storage import storage
from question_bank.extraction.asset_detector import detect_visual_assets
from question_bank.extraction.question_boundary import detect_question_boundaries
from question_bank.extraction.page_renderer import render_region

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__import__("os").getenv("QUESTION_ASSET_DIR", PROJECT_ROOT / "question_assets"))
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def _union_rects(rects: list[tuple[float, float, float, float]], page_rect: fitz.Rect) -> fitz.Rect | None:
    if not rects:
        return None
    result = fitz.Rect(rects[0]) & page_rect
    for rect in rects[1:]:
        result |= fitz.Rect(rect) & page_rect
    return result if result.get_area() > 0 else None


def persist_source_visuals(
    pdf_path: str | Path,
    page_number: int,
    question_number: str,
    question_id: str,
) -> list[dict[str, Any]]:
    """Extract one consolidated visual region from the source PDF and persist it.

    The asset is derived from detected image/vector regions inside the question
    boundary. It is never generated from the AI's visual reference string.
    """
    pdf_path = Path(pdf_path)
    question_number = str(question_number).strip()
    with fitz.open(str(pdf_path)) as document:
        if page_number < 1 or page_number > len(document):
            return []
        page = document[page_number - 1]
        boundaries = detect_question_boundaries(page, page_number)
        boundary = next((b for b in boundaries if str(b.question_number) == question_number), None)
        if boundary is None:
            return []
        visuals = detect_visual_assets(page, page_number, boundary.bbox)
        if not visuals:
            return []
        rect = _union_rects([a.bbox for a in visuals], page.rect)
        if rect is None:
            return []

        asset_id = f"{question_id}-visual-01"
        existing = storage.get_question_assets(question_id)
        if any(str(row.get("asset_id")) == asset_id for row in existing):
            return [dict(row) for row in existing if str(row.get("asset_id")) == asset_id]

        output_dir = ASSET_DIR / question_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "visual_01.png"
        render_region(page, tuple(rect), output_path, dpi=200)
        storage.create_question_asset(
            asset_id=asset_id,
            question_id=question_id,
            asset_type="visual",
            original_filename=output_path.name,
            file_path=str(output_path),
        )
        return [{
            "asset_id": asset_id,
            "question_id": question_id,
            "asset_type": "visual",
            "original_filename": output_path.name,
            "file_path": str(output_path),
            "source_page": page_number,
            "source_bbox": tuple(rect),
        }]
