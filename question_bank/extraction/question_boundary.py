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

# In the supported CBSE board-paper layout, top-level question numbers begin
# at the left text margin. A tighter threshold avoids numeric labels used in
# diagrams and internal choices while remaining independent of page numbers.
LEFT_MARGIN_RATIO = 0.10


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


def _is_left_margin_marker(page: fitz.Page, x0: float) -> bool:
    return x0 <= page.rect.width * LEFT_MARGIN_RATIO


def _question_markers(page: fitz.Page) -> list[tuple[str, float]]:
    """Return likely top-level question numbers and their y positions."""
    markers: list[tuple[str, float]] = []
    seen: set[tuple[str, int]] = set()

    for word in _words(page):
        x0, y0, x1, y1, text = word[:5]
        if not _is_left_margin_marker(page, float(x0)):
            continue
        match = QUESTION_RE.match(text.strip())
        if not match:
            continue
        number = match.group(1)
        key = (number, round(y0))
        if key not in seen:
            seen.add(key)
            markers.append((number, float(y0)))

    # Some PDFs combine a question number and its first word into one token.
    # Keep this fallback subject to the same left-margin safety rule.
    if not markers:
        for word in _words(page):
            x0, y0, x1, y1, text = word[:5]
            if not _is_left_margin_marker(page, float(x0)):
                continue
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

    The final question extends to the bottom of the page. Cross-page question
    merging is intentionally deferred to a later version because it requires
    document-level context.
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

        # Use the complete horizontal page width so diagrams/tables beside or
        # below the question text remain part of the source-of-truth crop.
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
