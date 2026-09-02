"""V1 orchestration for extracting visual question crops from PDF pages."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from question_bank.extraction.asset_detector import detect_visual_assets
from question_bank.extraction.page_renderer import render_region
from question_bank.extraction.question_boundary import detect_question_boundaries


def extract_page_questions(
    pdf_path: str | Path,
    page_number: int,
    output_dir: str | Path,
    dpi: int = 180,
) -> list[dict[str, Any]]:
    """Extract top-level question crops from one 1-based PDF page."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with fitz.open(str(pdf_path)) as document:
        if page_number < 1 or page_number > len(document):
            raise ValueError(f"Page {page_number} is outside the PDF")
        page = document[page_number - 1]
        boundaries = detect_question_boundaries(page, page_number)

        results: list[dict[str, Any]] = []
        for boundary in boundaries:
            filename = f"Q{boundary.question_number}.png"
            crop_path = render_region(
                page,
                boundary.bbox,
                output_dir / filename,
                dpi=dpi,
            )
            assets = detect_visual_assets(page, page_number, boundary.bbox)
            results.append(
                {
                    "question_number": boundary.question_number,
                    "source_page": page_number,
                    "bbox": boundary.bbox,
                    "confidence": boundary.confidence,
                    "crop_path": str(crop_path),
                    "assets": [asset.to_dict() for asset in assets],
                }
            )

        return results
