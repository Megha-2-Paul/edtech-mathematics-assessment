import pytest

from exam_platform.ingestion.models import IngestionCandidate, NormalizedQuestion, ValidationResult
from exam_platform.ingestion.review import QuestionReviewService


def _candidate():
    return IngestionCandidate(
        question=NormalizedQuestion(
            raw_question_id="Q1",
            question_type="saq",
            answer_mode="final_answer_selection_and_handwritten_upload",
            question_text="Solve x + 2 = 5.",
            marks=2,
            subject="Mathematics",
            board="CBSE",
            class_level=10,
            chapter="Linear Equations in Two Variables",
        ),
        status="review_required",
        validation=ValidationResult(is_valid=True, confidence=0.9),
        provenance={"rights_status": "licensed"},
    )


def test_approval_requires_explicit_rights_confirmation():
    candidate = _candidate()
    service = QuestionReviewService()

    with pytest.raises(ValueError, match="rights/licensing"):
        service.approve(candidate, reviewer="Megha")

    decision = service.approve(
        candidate,
        reviewer="Megha",
        rights_confirmed=True,
        note="Source rights verified.",
    )
    assert candidate.status == "approved"
    assert decision.action == "approved"
    assert decision.rights_confirmed is True


def test_rejection_and_outdated_are_explicit_states():
    service = QuestionReviewService()

    rejected = _candidate()
    decision = service.reject(rejected, reviewer="Megha", note="Poor extraction.")
    assert rejected.status == "rejected"
    assert decision.action == "rejected"

    outdated = _candidate()
    decision = service.mark_outdated(outdated, reviewer="Megha", note="Old syllabus.")
    assert outdated.status == "outdated"
    assert decision.action == "outdated"
