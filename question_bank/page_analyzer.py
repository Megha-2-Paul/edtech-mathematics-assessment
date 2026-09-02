"""Render-first local page routing for question-paper PDFs.

The analyzer answers one question only: which PDF pages should move to the
question-extraction stage. It does not create question records and does not
call external APIs.

Routing combines native PDF text, rendered-page structure, and adjacent-page
similarity. Native text is a routing signal, not the source of truth for later
question extraction.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader

ENGLISH_MARKERS = (
    "question", "section", "general instructions", "find", "prove",
    "show that", "calculate", "solve", "figure", "case study", "marks",
)
HINDI_UNICODE_RE = re.compile(r"[\u0900-\u097F]")
QUESTION_NUMBER_RE = re.compile(
    r"(?:^|\s)(?:Q\.?\s*)?(\d{1,2})\s*[.)](?=\s|$)", re.I
)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _question_numbers(text: str) -> list[int]:
    numbers = [int(n) for n in QUESTION_NUMBER_RE.findall(text or "")]
    return sorted(set(n for n in numbers if 1 <= n <= 100))


def _question_range(text: str) -> tuple[int | None, int | None]:
    numbers = _question_numbers(text)
    return (numbers[0], numbers[-1]) if numbers else (None, None)


def _english_score(text: str) -> float:
    cleaned = _clean_text(text)
    if not cleaned:
        return 0.0
    marker_hits = sum(1 for marker in ENGLISH_MARKERS if marker in cleaned.lower())
    ascii_letters = len(re.findall(r"[A-Za-z]", cleaned))
    devanagari = len(HINDI_UNICODE_RE.findall(cleaned))
    letter_total = ascii_letters + devanagari
    language_ratio = ascii_letters / letter_total if letter_total else 0.0
    marker_score = min(1.0, marker_hits / 5.0)
    return round(0.7 * language_ratio + 0.3 * marker_score, 3)


def _looks_tabular(text: str) -> bool:
    if re.search(r"\b(table|frequency|cumulative|class|age|number of)\b", text, re.I):
        return True
    numeric_lines = sum(
        len(re.findall(r"\d+(?:\.\d+)?", line)) >= 3
        for line in (text or "").splitlines()
    )
    return numeric_lines >= 2


def _image_count(page: Any) -> int:
    try:
        return len(page.images)
    except Exception:
        return 0


def _numeric_signature(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def _text_similarity(left: str, right: str) -> float:
    a = _clean_text(left).lower()
    b = _clean_text(right).lower()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _render_page(page: Any, width: int = 64) -> bytes:
    """Render a page to a small grayscale fingerprint."""
    rect = page.rect
    scale = width / max(rect.width, 1)
    pix = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale),
        colorspace=fitz.csGRAY,
        alpha=False,
    )
    return bytes(pix.samples)


def _image_similarity(left: bytes | None, right: bytes | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    difference = sum(abs(a - b) for a, b in zip(left, right)) / (255 * len(left))
    return round(max(0.0, 1.0 - difference), 3)


def _duplicate_score(previous: dict[str, Any], current: dict[str, Any]) -> float:
    previous_numbers = set(previous["numeric_signature"])
    current_numbers = set(current["numeric_signature"])
    shared_numeric = previous_numbers & current_numbers
    numeric_ratio = len(shared_numeric) / max(1, len(previous_numbers | current_numbers))
    same_range = (
        previous["question_start"] is not None
        and previous["question_start"] == current["question_start"]
        and previous["question_end"] == current["question_end"]
    )
    image_score = _image_similarity(
        previous.get("image_fingerprint"), current.get("image_fingerprint")
    )
    text_score = _text_similarity(previous["text"], current["text"])
    return round(
        0.72 * image_score
        + 0.12 * numeric_ratio
        + (0.10 if same_range else 0.0)
        + 0.06 * text_score,
        3,
    )


def analyze_page(page: Any, page_number: int, render: bool = False) -> dict[str, Any]:
    """Analyze one page using native text and optional local rendering."""
    text = page.get_text("text") if hasattr(page, "get_text") else page.extract_text() or ""
    numbers = _question_numbers(text)
    start, end = _question_range(text)
    score = _english_score(text)
    images = _image_count(page)
    has_figure_reference = bool(re.search(r"\b(fig(?:ure)?\.?|diagram|graph)\b", text, re.I))
    devanagari = bool(HINDI_UNICODE_RE.search(text))
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    hindi_letters = len(HINDI_UNICODE_RE.findall(text))

    is_question_page = bool(numbers) or bool(re.search(r"\bquestion(?:s)?\b", text, re.I))
    if score >= 0.55 and not devanagari:
        language = "english"
    elif hindi_letters > ascii_letters and hindi_letters:
        language = "non_english"
    elif is_question_page and score >= 0.35:
        language = "mixed_or_unknown"
    else:
        language = "mixed_or_unknown"

    fingerprint = _render_page(page) if render else None
    return {
        "page": page_number,
        "language": language,
        "english_score": score,
        "is_question_page": is_question_page,
        "question_numbers": numbers,
        "question_start": start,
        "question_end": end,
        "has_tables": _looks_tabular(text),
        "image_count": images,
        "has_figures": bool(images or has_figure_reference),
        "extracted_text_length": len(text),
        "needs_visual_review": False,
        "routing": "extract_vision" if is_question_page else "skip",
        "confidence": 0.0,
        "likely_duplicate_language_page": False,
        "paired_english_page": None,
        "duplicate_score": 0.0,
        "text": text,
        "numeric_signature": _numeric_signature(text),
        "image_fingerprint": fingerprint,
    }


def _classify_and_route(results: list[dict[str, Any]]) -> None:
    for result in results:
        if not result["is_question_page"]:
            result["routing"] = "skip"
            result["confidence"] = 0.95
        elif result["language"] == "english":
            result["routing"] = "extract_vision"
            result["confidence"] = min(0.99, 0.65 + 0.35 * result["english_score"])
        elif result["language"] == "non_english":
            result["routing"] = "manual_review"
            result["confidence"] = 0.75
        else:
            result["routing"] = "manual_review"
            result["confidence"] = 0.50

    for previous, current in zip(results, results[1:]):
        score = _duplicate_score(previous, current)
        if score < 0.65 or not previous["is_question_page"] or not current["is_question_page"]:
            continue
        if previous["language"] == current["language"]:
            continue
        english = previous if previous["language"] == "english" else current if current["language"] == "english" else None
        non_english = previous if previous["language"] == "non_english" else current if current["language"] == "non_english" else None
        if english is None or non_english is None:
            continue
        non_english["likely_duplicate_language_page"] = True
        non_english["paired_english_page"] = english["page"]
        non_english["duplicate_score"] = score
        english["duplicate_score"] = score
        non_english["routing"] = "skip_duplicate"
        english["routing"] = "extract_vision"

    for result in results:
        result["needs_visual_review"] = result["routing"] == "manual_review"


def analyze_pdf(file_path: str) -> list[dict[str, Any]]:
    """Render and analyze every page; return extraction routing metadata."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Source file must be a PDF")

    try:
        document = fitz.open(str(path))
        results = [analyze_page(page, i, render=True) for i, page in enumerate(document, 1)]
        document.close()
    except Exception:
        reader = PdfReader(str(path))
        results = [analyze_page(page, i, render=False) for i, page in enumerate(reader.pages, 1)]

    _classify_and_route(results)
    for result in results:
        result.pop("text", None)
        result.pop("numeric_signature", None)
        result.pop("image_fingerprint", None)
    return results


def analyze_pdf_summary(file_path: str) -> dict[str, Any]:
    """Return compact routing metadata for logs/CLI output."""
    pages = analyze_pdf(file_path)
    english = [p for p in pages if p["routing"] == "extract_vision"]
    duplicates = [p for p in pages if p["routing"] == "skip_duplicate"]
    return {
        "page_count": len(pages),
        "question_pages": sum(p["is_question_page"] for p in pages),
        "english_question_pages": len(english),
        "likely_duplicate_pages": len(duplicates),
        "visual_review_pages": sum(p["needs_visual_review"] for p in pages),
        "pages": pages,
    }
