from pathlib import Path

import fitz

from question_bank.extraction.extraction_router import (
    ExtractionStrategy,
    inspect_pdf,
    route_pdf,
)
from question_bank.extraction.markitdown_extractor import MarkItDownPDFExtractor


def _make_text_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (50, 60),
        "1. Solve x² − 5x + 6 = 0.\n"
        "2. If sin θ = 1/2, find cos θ.\n"
        "3. Choose the correct answer.\n"
        "(A) 1\n(B) 2\n(C) 3\n(D) 4\n",
    )
    document.save(path)
    document.close()


def _make_image_only_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 300, 120), 0)
    pixmap.clear_with(255)
    page.insert_image(fitz.Rect(20, 20, 280, 100), pixmap=pixmap)
    document.save(path)
    document.close()
    pixmap = None


def test_markitdown_extracts_text_from_text_pdf(tmp_path):
    pdf_path = tmp_path / "math-paper.pdf"
    _make_text_pdf(pdf_path)

    result = MarkItDownPDFExtractor().extract(pdf_path)

    assert result.extraction_method == "markitdown"
    assert not result.is_empty
    assert "x" in result.text
    assert "sin" in result.text


def test_pdf_router_selects_markitdown_for_text_dominant_pdf(tmp_path):
    pdf_path = tmp_path / "text.pdf"
    _make_text_pdf(pdf_path)

    inspection = inspect_pdf(pdf_path)
    route = route_pdf(pdf_path)

    assert inspection.page_count == 1
    assert inspection.text_pages == 1
    assert route.strategy == ExtractionStrategy.MARKITDOWN
    assert route.reason == "text_dominant_pdf"


def test_pdf_router_hands_image_only_pdf_to_future_ocr(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    _make_image_only_pdf(pdf_path)

    inspection = inspect_pdf(pdf_path)
    route = route_pdf(pdf_path)

    assert inspection.page_count == 1
    assert inspection.text_pages == 0
    assert inspection.image_pages == 1
    assert route.strategy == ExtractionStrategy.OCR
    assert route.reason == "no_usable_text_layer"
