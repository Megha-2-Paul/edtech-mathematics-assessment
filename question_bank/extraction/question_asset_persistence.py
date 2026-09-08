"""Persist source-PDF visual assets for approved canonical questions."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import os

import fitz

from exam_platform.storage import storage
from question_bank.extraction.asset_detector import VisualAsset, detect_visual_assets
from question_bank.extraction.question_boundary import detect_question_boundaries
from question_bank.extraction.page_renderer import render_region

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(os.getenv("QUESTION_ASSET_DIR", PROJECT_ROOT / "question_assets"))
ASSET_DIR.mkdir(parents=True, exist_ok=True)

# Conservative settings for PDF vector diagrams. Text glyphs can also appear as
# vector drawings in some PDFs, so we cluster drawing rectangles and prefer the
# largest coherent graphic component instead of unioning every drawing on the
# question page.
DRAWING_CLUSTER_GAP = 10.0
VISUAL_PADDING = 12.0
TEXT_OVERLAP_RATIO = 0.55
# Exam PDFs commonly place QR codes and other document metadata in a narrow
# footer band. They are page artifacts, not question visuals, and must not be
# persisted as assets for the question above them.
FOOTER_EXCLUSION_PT = 55.0
SMALL_FOOTER_IMAGE_MAX_PT = 110.0


def _rect_area(rect: fitz.Rect) -> float:
    return max(0.0, rect.get_area())


def _overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    overlap = a & b
    area = _rect_area(a)
    return _rect_area(overlap) / area if area else 0.0


def _looks_like_footer_artifact(page: fitz.Page, rect: fitz.Rect, asset_type: str) -> bool:
    """Reject small page-footer images such as QR codes from question assets."""
    if asset_type != "image":
        return False

    # Only apply the footer rule to compact images. A legitimate full-width
    # figure near the bottom of a question should remain eligible.
    width = max(0.0, rect.width)
    height = max(0.0, rect.height)
    compact = width <= SMALL_FOOTER_IMAGE_MAX_PT and height <= SMALL_FOOTER_IMAGE_MAX_PT
    in_footer = rect.y1 >= page.rect.y1 - FOOTER_EXCLUSION_PT
    return compact and in_footer


def _text_rects(page: fitz.Page) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    try:
        for block in page.get_text("blocks"):
            if len(block) >= 4:
                rect = fitz.Rect(block[:4]) & page.rect
                if _rect_area(rect) > 0:
                    rects.append(rect)
    except (AttributeError, RuntimeError):
        pass
    return rects


def _graphic_candidates(
    page: fitz.Page,
    page_number: int,
    region: fitz.Rect,
) -> list[VisualAsset]:
    """Return graphic candidates while suppressing text-like vector drawings."""
    detected = detect_visual_assets(page, page_number, tuple(region))
    if not detected:
        return []

    text_rects = _text_rects(page)
    candidates: list[VisualAsset] = []

    for asset in detected:
        rect = fitz.Rect(asset.bbox) & region
        if _rect_area(rect) <= 0:
            continue

        # Footer QR codes/document metadata are page artifacts, not question
        # visuals. Filter them before native images are automatically preferred.
        if _looks_like_footer_artifact(page, rect, asset.asset_type):
            continue

        # Native PDF images are already reliable visual objects.
        if asset.asset_type == "image":
            candidates.append(asset)
            continue

        # Vector PDFs sometimes represent letters and text fragments as
        # drawings. Remove a drawing when most of its area lies inside a text
        # block. Real diagram lines may touch labels but usually do not occupy
        # most of a text block.
        if any(_overlap_ratio(rect, text_rect) >= TEXT_OVERLAP_RATIO for text_rect in text_rects):
            continue
        candidates.append(asset)

    return candidates


def _clusters(rects: list[fitz.Rect], gap: float) -> list[fitz.Rect]:
    """Merge nearby/overlapping rectangles into coherent visual components."""
    components: list[fitz.Rect] = []
    pending = list(rects)

    while pending:
        current = pending.pop(0)
        changed = True
        while changed:
            changed = False
            expanded = fitz.Rect(
                current.x0 - gap,
                current.y0 - gap,
                current.x1 + gap,
                current.y1 + gap,
            )
            remaining: list[fitz.Rect] = []
            for rect in pending:
                if _rect_area(expanded & rect) > 0:
                    current |= rect
                    changed = True
                else:
                    remaining.append(rect)
            pending = remaining
        components.append(current)

    return components


def _best_visual_rect(
    page: fitz.Page,
    candidates: list[VisualAsset],
    question_region: fitz.Rect,
) -> fitz.Rect | None:
    if not candidates:
        return None

    image_rects = [
        fitz.Rect(a.bbox) & question_region
        for a in candidates
        if a.asset_type == "image"
    ]
    drawing_rects = [
        fitz.Rect(a.bbox) & question_region
        for a in candidates
        if a.asset_type == "drawing"
    ]

    # Prefer native images when present; multiple image fragments are merged.
    if image_rects:
        return max(
            _clusters(image_rects, DRAWING_CLUSTER_GAP),
            key=_rect_area,
        )

    if not drawing_rects:
        return None

    components = _clusters(drawing_rects, DRAWING_CLUSTER_GAP)
    # Diagram/vector components normally occupy substantially more coherent
    # area than isolated text glyphs or small decorative marks.
    return max(components, key=_rect_area)


def persist_source_visuals(
    pdf_path: str | Path,
    page_number: int,
    question_number: str,
    question_id: str,
) -> list[dict[str, Any]]:
    """Persist the best source-PDF visual associated with one question.

    The stored file is a real crop from the original PDF. AI references such as
    ``figure_1`` are metadata only and are never treated as image data.
    Existing asset records are refreshed in place so a corrected detector can
    repair an already-approved question without creating duplicate assets.
    """
    pdf_path = Path(pdf_path)
    question_number = str(question_number).strip()

    with fitz.open(str(pdf_path)) as document:
        if page_number < 1 or page_number > len(document):
            return []

        page = document[page_number - 1]
        boundaries = detect_question_boundaries(page, page_number)
        boundary = next(
            (b for b in boundaries if str(b.question_number) == question_number),
            None,
        )
        if boundary is None:
            return []

        question_region = fitz.Rect(boundary.bbox) & page.rect
        candidates = _graphic_candidates(page, page_number, question_region)
        rect = _best_visual_rect(page, candidates, question_region)
        if rect is None or _rect_area(rect) <= 0:
            return []

        # Add a small amount of whitespace so diagram labels near the vector
        # lines remain visible, while never escaping the question boundary.
        rect = fitz.Rect(
            max(question_region.x0, rect.x0 - VISUAL_PADDING),
            max(question_region.y0, rect.y0 - VISUAL_PADDING),
            min(question_region.x1, rect.x1 + VISUAL_PADDING),
            min(question_region.y1, rect.y1 + VISUAL_PADDING),
        )
        if _rect_area(rect) <= 0:
            return []

        asset_id = f"{question_id}-visual-01"
        existing = storage.get_question_assets(question_id)

        output_dir = ASSET_DIR / question_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "visual_01.png"

        # Always regenerate the source crop. This is important when an asset
        # was created by an older detector and the detector has since been
        # corrected.
        render_region(page, tuple(rect), output_path, dpi=220)

        existing_row = next(
            (dict(row) for row in existing if str(row.get("asset_id")) == asset_id),
            None,
        )
        if existing_row:
            existing_row["file_path"] = str(output_path)
            existing_row["source_page"] = page_number
            existing_row["source_bbox"] = tuple(rect)
            return [existing_row]

        storage.create_question_asset(
            asset_id=asset_id,
            question_id=question_id,
            asset_type="visual",
            original_filename=output_path.name,
            file_path=str(output_path),
        )
        return [
            {
                "asset_id": asset_id,
                "question_id": question_id,
                "asset_type": "visual",
                "original_filename": output_path.name,
                "file_path": str(output_path),
                "source_page": page_number,
                "source_bbox": tuple(rect),
            }
        ]
