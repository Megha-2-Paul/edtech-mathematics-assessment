"""Explicit human-review state transitions for ingestion candidates.

This module deliberately does not persist or publish questions. A later integration
can connect approved candidates to the existing question-bank persistence layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import IngestionCandidate, IngestionStatus
from .pipeline import QuestionIngestionPipeline


@dataclass(frozen=True)
class ReviewDecision:
    """Audit-friendly representation of a review action."""

    action: str
    reviewer: str
    note: Optional[str] = None
    rights_confirmed: bool = False


class QuestionReviewService:
    """Apply explicit review decisions without auto-publishing candidates."""

    def approve(
        self,
        candidate: IngestionCandidate,
        *,
        reviewer: str,
        rights_confirmed: bool = False,
        note: Optional[str] = None,
    ) -> ReviewDecision:
        if not reviewer.strip():
            raise ValueError("Reviewer is required.")
        if not QuestionIngestionPipeline.publishable(candidate):
            raise ValueError("Only valid, non-duplicate review candidates can be approved.")
        if not rights_confirmed:
            raise ValueError("Explicit rights/licensing confirmation is required before approval.")

        candidate.status = IngestionStatus.APPROVED.value
        return ReviewDecision(
            action="approved",
            reviewer=reviewer.strip(),
            note=note,
            rights_confirmed=True,
        )

    @staticmethod
    def reject(
        candidate: IngestionCandidate,
        *,
        reviewer: str,
        note: Optional[str] = None,
    ) -> ReviewDecision:
        if not reviewer.strip():
            raise ValueError("Reviewer is required.")
        candidate.status = IngestionStatus.REJECTED.value
        return ReviewDecision(action="rejected", reviewer=reviewer.strip(), note=note)

    @staticmethod
    def mark_outdated(
        candidate: IngestionCandidate,
        *,
        reviewer: str,
        note: Optional[str] = None,
    ) -> ReviewDecision:
        if not reviewer.strip():
            raise ValueError("Reviewer is required.")
        candidate.status = IngestionStatus.OUTDATED.value
        return ReviewDecision(action="outdated", reviewer=reviewer.strip(), note=note)
