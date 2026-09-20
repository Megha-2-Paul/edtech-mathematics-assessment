"""Route PDFs to an appropriate first-stage extraction strategy.

The router intentionally makes conservative decisions. It does not attempt
OCR or AI extraction yet; those strategies are represented so they can be
added without changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz


class ExtractionStrategy(str, Enum):
    MARKITDOWN = "markitdown"
    PYMUPDF_LAYOUT = "pymupdf_layout"
    OCR = "ocr"
    AI_VISION = "ai_vision"


@dataclass(frozen=True)
class PDFInspection:
    page_count: int
    text_pages: int
    image_pages: int
    text_char_count: int
    image_count: int

    @property
    def text_page_ratio(self) -> float:
        return self.text_pages / self.page_count if self.page_count else 0.0

    @property
    def image_page_ratio(self) -> float:
        return self.image_pages / self.page_count if self.page_count else 0.0


@dataclass(frozen=True)
class ExtractionRoute:
    strategy: ExtractionStrategy
    reason: str
    inspection: PDFInspection


def inspect_pdf(file_path: str | Path) -> PDFInspection:
    """Inspect a PDF without running an extractor."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("PDF inspection requires a .pdf file.")

    with fitz.open(path) as document:
        text_pages = 0
        image_pages = 0
        text_char_count = 0
        image_count = 0

        for page in document:
            text = (page.get_text("text") or "").strip()
            images = page.get_images(full=True)

            if text:
                text_pages += 1
                text_char_count += len(text)
            if images:
                image_pages += 1
                image_count += len(images)

        return PDFInspection(
            page_count=len(document),
            text_pages=text_pages,
            image_pages=image_pages,
            text_char_count=text_char_count,
            image_count=image_count,
        )


def route_pdf(file_path: str | Path) -> ExtractionRoute:
    """Select the safest currently implemented extraction strategy.

    Text-dominant PDFs are routed to MarkItDown. PDFs with substantial visual
    content stay on the existing PyMuPDF/layout path so page geometry and
    source visuals are preserved. Image-only PDFs are handed off to the future
    OCR path.
    """
    inspection = inspect_pdf(file_path)

    if inspection.page_count == 0:
        return ExtractionRoute(
            ExtractionStrategy.PYMUPDF_LAYOUT,
            "empty_pdf",
            inspection,
        )

    if inspection.text_pages == 0:
        return ExtractionRoute(
            ExtractionStrategy.OCR,
            "no_usable_text_layer",
            inspection,
        )

    if inspection.text_page_ratio >= 0.90 and inspection.image_page_ratio <= 0.35:
        return ExtractionRoute(
            ExtractionStrategy.MARKITDOWN,
            "text_dominant_pdf",
            inspection,
        )

    return ExtractionRoute(
        ExtractionStrategy.PYMUPDF_LAYOUT,
        "visual_or_mixed_layout_requires_page_geometry",
        inspection,
    )
