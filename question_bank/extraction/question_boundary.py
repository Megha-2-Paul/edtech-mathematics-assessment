"""Detect top-level question boundaries on a single PDF page.

V1 deliberately detects only top-level numbered questions. It uses PyMuPDF
word coordinates so that the physical region can be rendered without losing
nearby diagrams, tables, or internal choices.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any

import fitz


QUESTION_RE = re.compile(r"^(?:Q\.?\s*)?(\d{1,2})[.)]$", re.IGNORECASE)
QUESTION_INLINE_RE = re.compile(r"^(?:Q\.?\s*)?(\d{1,2})[.)]\s+", re.IGNORECASE)


@dataclass(frozen=True)
class QuestionBoundary:
    question_number: str
    page: int
    bbox: tuple[float, float, float, float]
    start_y: float
    end_y: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _words(page: fitz.Page) -> list[tuple]:
    return page.get_text("words") or []


def _question_markers(page: fitz.Page) -> list[tuple[str, float]]:
    """Return top-level question numbers and their y positions.

    Only standalone numeric markers are accepted here. Subparts such as
    ``(a)``/``(b)`` therefore cannot accidentally become questions.
    """
    markers: list[tuple[str, float]] = []
    seen: set[tuple[str, int]] = set()

    for word in _words(page):
        x0, y0, x1, y1, text = word[:5]
        cleaned = text.strip()
        match = QUESTION_RE.match(cleaned)
        if not match:
            # Some PDFs split the number and punctuation into separate words.
            continue
        number = match.group(1)
        key = (number, round(y0))
        if key not in seen:
            seen.add(key)
            markers.append((number, float(y0)))

    # A question number can occasionally be embedded in a larger token.
    # Handle that conservatively only when the token begins with a number and
    # punctuation, and never treat subparts as top-level questions.
    if not markers:
        for word in _words(page):
            x0, y0, x1, y1, text = word[:5]
            match = QUESTION_INLINE_RE.match(text.strip())
            if match:
                number = match.group(1)
                key = (number, round(y0))
                if key not in seen:
                    seen.add(key)
                    markers.append((number, float(y0)))

    markers.sort(key=lambda item: item[1])
    return markers


def detect_question_boundaries(page: fitz.Page, page_number: int) -> list[QuestionBoundary]:
    """Detect top-level question regions on ``page``.

    The final question extends to the bottom of the page. The caller can
    merge adjacent regions across pages in a later version when a question
    genuinely continues onto the next page.
    """
    markers = _question_markers(page)
    if not markers:
        return []

    page_rect = page.rect
    boundaries: list[QuestionBoundary] = []

    for index, (number, start_y) in enumerate(markers):
        end_y = markers[index + 1][1] if index + 1 < len(markers) else page_rect.height
        if end_y <= start_y:
            continue

        # Include the complete horizontal page width. This is intentional in
        # V1: visual content can sit beside or below the question text.
        bbox = (0.0, start_y, page_rect.width, end_y)
        boundaries.append(
            QuestionBoundary(
                question_number=number,
                page=page_number,
                bbox=bbox,
                start_y=start_y,
                end_y=end_y,
                confidence=0.90,
            )
        )

    return boundaries
