"""Detect top-level question boundaries on a single PDF page.

V1.1 keeps the V1 coordinate-based approach but makes question-marker
selection more conservative: CBSE top-level question numbers share a stable
left text margin, while ordinary numbers inside question text can be indented.
Only the left-margin candidate cluster is accepted.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any

import fitz


QUESTION_RE = re.compile(r"^(?:Q\.?\s*)?(\d{1,2})[.)]$", re.IGNORECASE)
QUESTION_INLINE_RE = re.compile(r"^(?:Q\.?\s*)?(\d{1,2})[.)]\s+", re.IGNORECASE)

# First restrict candidates to the broad left side. We then identify the
# actual question-marker x-position from the leftmost candidate cluster.
LEFT_MARGIN_RATIO = 0.15
LEFT_MARKER_TOLERANCE_PT = 30.0


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


def _candidate_markers(page: fitz.Page) -> list[tuple[str, float, float]]:
    """Collect numeric question-marker candidates on the broad left side."""
    candidates: list[tuple[str, float, float]] = []
    seen: set[tuple[str, int]] = set()
    for word in _words(page):
        x0, y0, _x1, _y1, text = word[:5]
        if x0 > page.rect.width * LEFT_MARGIN_RATIO:
            continue
        match = QUESTION_RE.match(text.strip())
        if not match:
            continue
        number = match.group(1)
        key = (number, round(y0))
        if key not in seen:
            seen.add(key)
            candidates.append((number, float(y0), float(x0)))

    if candidates:
        return candidates

    # Some PDFs combine a number and the first word into one text token.
    for word in _words(page):
        x0, y0, _x1, _y1, text = word[:5]
        if x0 > page.rect.width * LEFT_MARGIN_RATIO:
            continue
        match = QUESTION_INLINE_RE.match(text.strip())
        if not match:
            continue
        number = match.group(1)
        key = (number, round(y0))
        if key not in seen:
            seen.add(key)
            candidates.append((number, float(y0), float(x0)))
    return candidates


def _question_markers(page: fitz.Page) -> list[tuple[str, float]]:
    """Return likely top-level question numbers and their y positions."""
    candidates = _candidate_markers(page)
    if not candidates:
        return []

    # In the supported CBSE layout, genuine top-level markers start at the
    # same left margin. An indented number such as the ``10.`` at the end of
    # a sentence should therefore not be accepted merely because it is on the
    # broad left side of the page.
    marker_x = min(x0 for _number, _y0, x0 in candidates)
    candidates = [
        (number, y0)
        for number, y0, x0 in candidates
        if x0 <= marker_x + LEFT_MARKER_TOLERANCE_PT
    ]
    candidates.sort(key=lambda item: item[1])
    return candidates


def detect_question_boundaries(page: fitz.Page, page_number: int) -> list[QuestionBoundary]:
    """Detect top-level question regions on ``page``.

    The final question extends to the bottom of the page. Cross-page question
    merging is intentionally deferred to the document-level V1.1 review step.
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
                confidence=0.92,
            )
        )

    return boundaries
