"""Document-level checks for question-boundary continuity.

V1.1 does not automatically merge questions across pages. It identifies
pages where a question may continue or where the detected top-level sequence
looks suspicious, so a human can review the original PDF before approval.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Sequence


@dataclass(frozen=True)
class ContinuationReview:
    page: int
    detected_numbers: tuple[int, ...]
    previous_last_question: int | None
    first_question: int | None
    issues: tuple[str, ...]
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def review_page_sequence(
    page: int,
    question_numbers: Sequence[int],
    previous_last_question: int | None,
) -> ContinuationReview:
    """Review one page against the preceding English question page.

    A missing marker is explicitly treated as a review signal because a
    question may continue onto the page without repeating its number.
    Numeric gaps are also flagged, but never auto-filled.
    """
    numbers = tuple(question_numbers)
    issues: list[str] = []
    severity = "ok"

    if not numbers:
        issues.append("no_top_level_question_marker")
        severity = "review"
    else:
        if len(numbers) != len(set(numbers)):
            issues.append("duplicate_question_marker_on_page")
            severity = "review"

        if any(current <= previous for previous, current in zip(numbers, numbers[1:])):
            issues.append("non_increasing_question_sequence")
            severity = "review"

        first = numbers[0]
        if previous_last_question is not None:
            expected = previous_last_question + 1
            if first == previous_last_question:
                issues.append("possible_repeated_or_continued_question")
                severity = "review"
            elif first < expected:
                issues.append("question_sequence_moves_backward")
                severity = "review"
            elif first > expected:
                issues.append("possible_missing_marker_or_unexpected_question_gap")
                severity = "review"

    return ContinuationReview(
        page=page,
        detected_numbers=numbers,
        previous_last_question=previous_last_question,
        first_question=numbers[0] if numbers else None,
        issues=tuple(issues),
        severity=severity,
    )


def review_document_sequences(
    page_questions: Sequence[tuple[int, Sequence[int]]],
) -> list[ContinuationReview]:
    """Review ordered English pages for suspicious question continuity."""
    reviews: list[ContinuationReview] = []
    previous_last: int | None = None

    for page, numbers in page_questions:
        review = review_page_sequence(page, numbers, previous_last)
        reviews.append(review)
        if numbers:
            previous_last = max(numbers)

    return reviews
