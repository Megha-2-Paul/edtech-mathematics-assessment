"""Conservative local analysis of question-paper PDF pages.

This layer does not call external APIs and does not create question-bank rows.
It produces routing metadata so later extraction can skip duplicate-language
pages and reserve expensive/limited vision extraction for uncertain pages.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ENGLISH_MARKERS = (
    "question", "section", "general instructions", "find", "prove",
    "show that", "calculate", "solve", "figure", "case study", "marks",
)
QUESTION_RANGE_PATTERNS = (
    re.compile(r"question\s+numbers?\s+(\d+)\s+to\s+(\d+)", re.I),
    re.compile(r"question\s+(\d+)", re.I),
)

def _question_range(text: str) -> tuple[int | None, int | None]:
    for pattern in QUESTION_RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.lastindex and match.lastindex >= 2 else start
            return start, end
    numbers = [int(n) for n in re.findall(r"(?m)^\s*(\d{1,2})\.\s", text)]
    return (min(numbers), max(numbers)) if numbers else (None, None)

def _english_score(text: str) -> float:
    lower = text.lower()
    return min(1.0, sum(1 for marker in ENGLISH_MARKERS if marker in lower) / 5.0)

def _looks_tabular(text: str) -> bool:
    if re.search(r"\b(table|frequency|cumulative|class|age|number of)\b", text, re.I):
        return True
    numeric_lines = sum(len(re.findall(r"\d+(?:\.\d+)?", line)) >= 3 for line in text.splitlines())
    return numeric_lines >= 2

def _image_count(page: Any) -> int:
    try:
        return len(page.images)
    except Exception:
        return 0

def analyze_page(page: Any, page_number: int) -> dict[str, Any]:
    """Analyze one pypdf page conservatively."""
    text = page.extract_text() or ""
    start, end = _question_range(text)
    score = _english_score(text)
    images = _image_count(page)
    has_figure_reference = bool(re.search(r"\b(fig(?:ure)?\.?|diagram|graph)\b", text, re.I))
    is_question_page = start is not None
    if score >= 0.6 and is_question_page:
        language = "english"
    elif score < 0.4 and is_question_page:
        language = "non_english_or_garbled"
    else:
        language = "mixed_or_unknown"
    return {
        "page": page_number,
        "language": language,
        "english_score": round(score, 3),
        "is_question_page": is_question_page,
        "question_start": start,
        "question_end": end,
        "has_tables": _looks_tabular(text),
        "image_count": images,
        "has_figures": bool(images or has_figure_reference),
        "extracted_text_length": len(text),
        "needs_visual_review": bool(images or score < 0.4),
        "likely_duplicate_language_page": False,
        "paired_english_page": None,
    }

def analyze_pdf(file_path: str) -> list[dict[str, Any]]:
    """Analyze every page and flag likely non-English duplicates conservatively."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Source file must be a PDF")
    reader = PdfReader(str(path))
    results = [analyze_page(page, i) for i, page in enumerate(reader.pages, 1)]
    for previous, current in zip(results, results[1:]):
        same_range = (
            previous["question_start"] == current["question_start"]
            and previous["question_end"] == current["question_end"]
            and previous["is_question_page"]
            and current["is_question_page"]
        )
        if same_range and current["language"] == "english" and previous["language"] != "english":
            previous["likely_duplicate_language_page"] = True
            previous["paired_english_page"] = current["page"]
    return results

def analyze_pdf_summary(file_path: str) -> dict[str, Any]:
    """Return a compact routing summary for logs/CLI output."""
    pages = analyze_pdf(file_path)
    return {
        "page_count": len(pages),
        "question_pages": sum(p["is_question_page"] for p in pages),
        "english_question_pages": sum(p["language"] == "english" for p in pages),
        "likely_duplicate_pages": sum(p["likely_duplicate_language_page"] for p in pages),
        "visual_review_pages": sum(p["needs_visual_review"] for p in pages),
        "pages": pages,
    }
