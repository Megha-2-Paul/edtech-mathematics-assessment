"""Local page routing for question-paper PDFs.

This layer intentionally does not extract questions or call external APIs.
It combines native PDF text with conservative layout/image signals and uses
adjacent-page similarity to identify likely bilingual duplicates. Exact
question boundaries are left to the extraction stage.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ENGLISH_MARKERS = (
    "question", "section", "general instructions", "find", "prove",
    "show that", "calculate", "solve", "figure", "case study", "marks",
)
HINDI_UNICODE_RE = re.compile(r"[\u0900-\u097F]")
QUESTION_NUMBER_RE = re.compile(r"(?m)^\s*(?:Q\.?|Question\s*)?(\d{1,2})\s*[.)]")


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _question_numbers(text: str) -> list[int]:
    numbers = [int(n) for n in QUESTION_NUMBER_RE.findall(text or "")]
    return sorted(set(numbers))


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
    # Strong language evidence comes from actual character distribution;
    # markers are supporting evidence only.
    letter_total = ascii_letters + devanagari
    language_ratio = ascii_letters / letter_total if letter_total else 0.0
    marker_score = min(1.0, marker_hits / 5.0)
    return round(0.7 * language_ratio + 0.3 * marker_score, 3)


def _looks_tabular(text: str) -> bool:
    if re.search(r"\b(table|frequency|cumulative|class|age|number of)\b", text, re.I):
        return True
    numeric_lines = sum(len(re.findall(r"\d+(?:\.\d+)?", line)) >= 3 for line in (text or "").splitlines())
    return numeric_lines >= 2


def _image_count(page: Any) -> int:
    try:
        return len(page.images)
    except Exception:
        return 0


def _text_similarity(left: str, right: str) -> float:
    """Similarity useful for bilingual duplicate detection, not OCR equality."""
    a = _clean_text(left).lower()
    b = _clean_text(right).lower()
    if not a or not b:
        return 0.0
    # Character-level similarity is deliberately only a weak signal because
    # English/Hindi text is different. Shared digits/question numbering help.
    return SequenceMatcher(None, a, b).ratio()


def _numeric_signature(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def _duplicate_score(previous: dict[str, Any], current: dict[str, Any]) -> float:
    same_numbers = previous["question_numbers"] == current["question_numbers"] and bool(previous["question_numbers"])
    shared_numeric = set(previous["numeric_signature"]) & set(current["numeric_signature"])
    numeric_ratio = len(shared_numeric) / max(1, len(set(previous["numeric_signature"] + current["numeric_signature"])))
    return round((0.6 if same_numbers else 0.0) + 0.3 * numeric_ratio + 0.1 * _text_similarity(previous["text"], current["text"]), 3)


def analyze_page(page: Any, page_number: int) -> dict[str, Any]:
    """Analyze one page using native PDF content only."""
    text = page.extract_text() or ""
    numbers = _question_numbers(text)
    start, end = _question_range(text)
    score = _english_score(text)
    images = _image_count(page)
    has_figure_reference = bool(re.search(r"\b(fig(?:ure)?\.?|diagram|graph)\b", text, re.I))
    devanagari = bool(HINDI_UNICODE_RE.search(text))
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    hindi_letters = len(HINDI_UNICODE_RE.findall(text))

    is_question_page = bool(numbers)
    if is_question_page and score >= 0.55 and not devanagari:
        language = "english"
    elif is_question_page and hindi_letters > ascii_letters:
        language = "non_english"
    elif is_question_page:
        language = "mixed_or_unknown"
    else:
        language = "mixed_or_unknown"

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
        # Visual review means the page contains material whose structure may
        # not be represented reliably by native text; it is not an instruction
        # to manually inspect every page.
        "needs_visual_review": bool(images or has_figure_reference or not text.strip()),
        "likely_duplicate_language_page": False,
        "paired_english_page": None,
        "duplicate_score": 0.0,
        "text": text,
        "numeric_signature": _numeric_signature(text),
    }


def analyze_pdf(file_path: str) -> list[dict[str, Any]]:
    """Analyze pages and conservatively flag adjacent bilingual duplicates."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Source file must be a PDF")

    reader = PdfReader(str(path))
    results = [analyze_page(page, i) for i, page in enumerate(reader.pages, 1)]

    # For common bilingual board-paper layouts, consecutive pages can be
    # language copies. Do not require exact question ranges: native extraction
    # often misses question labels. We use language direction + shared numeric
    # structure + adjacency, and only flag a pair when confidence is high.
    for previous, current in zip(results, results[1:]):
        score = _duplicate_score(previous, current)
        if (
            previous["is_question_page"]
            and current["is_question_page"]
            and previous["language"] == "non_english"
            and current["language"] == "english"
            and score >= 0.55
        ):
            previous["likely_duplicate_language_page"] = True
            previous["paired_english_page"] = current["page"]
            previous["duplicate_score"] = score
            current["duplicate_score"] = score

    for result in results:
        result.pop("text", None)
        result.pop("numeric_signature", None)

    return results


def analyze_pdf_summary(file_path: str) -> dict[str, Any]:
    """Return compact routing metadata for logs/CLI output."""
    pages = analyze_pdf(file_path)
    english = [p for p in pages if p["language"] == "english" and p["is_question_page"]]
    duplicates = [p for p in pages if p["likely_duplicate_language_page"]]
    return {
        "page_count": len(pages),
        "question_pages": sum(p["is_question_page"] for p in pages),
        "english_question_pages": len(english),
        "likely_duplicate_pages": len(duplicates),
        "visual_review_pages": sum(p["needs_visual_review"] for p in pages),
        "pages": pages,
    }
