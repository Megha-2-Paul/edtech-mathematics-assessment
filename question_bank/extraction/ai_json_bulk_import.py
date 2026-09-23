"""Bulk import orchestration for external-AI question JSON."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Optional
from exam_platform.ingestion.models import IngestionCandidate, IngestionStatus
from exam_platform.ingestion.pipeline import QuestionIngestionPipeline
from exam_platform.ingestion.review import QuestionReviewService, ReviewDecision
from exam_platform.models import ContentBlock, Question
from question_bank.extraction.ai_json_extractor import AIJSONQuestionExtractor

@dataclass
class BulkImportSummary:
    total: int = 0
    review_required: int = 0
    validation_pending: int = 0
    duplicates: int = 0
    invalid: int = 0
    candidates: list[IngestionCandidate] = field(default_factory=list)
    @property
    def publishable(self) -> int:
        return self.review_required

class AIJSONBulkImporter:
    """Convert one external-AI JSON batch into shared review candidates."""
    def __init__(self, *, existing_questions: Optional[Iterable[object]] = None):
        self.pipeline = QuestionIngestionPipeline(existing_questions=existing_questions)
    def prepare(self, payload: dict | list | str) -> BulkImportSummary:
        extractor = AIJSONQuestionExtractor(payload)
        source = extractor.to_source_document()
        candidates = self.pipeline.prepare(extractor.extract(), source)
        result = BulkImportSummary(total=len(candidates), candidates=candidates)
        for candidate in candidates:
            if candidate.status == IngestionStatus.REVIEW_REQUIRED.value:
                result.review_required += 1
            elif candidate.status == IngestionStatus.DUPLICATE.value:
                result.duplicates += 1
            elif candidate.status == IngestionStatus.VALIDATION_PENDING.value:
                result.validation_pending += 1
                if candidate.validation and candidate.validation.errors:
                    result.invalid += 1
        return result

def candidate_to_question(candidate: IngestionCandidate, *, question_id: str) -> Question:
    q = candidate.question
    choices = []
    for choice in q.answer_choices:
        if isinstance(choice, dict):
            label = str(choice.get("label") or "").strip()
            value = str(choice.get("text") or "").strip()
            choices.append(f"{label}) {value}" if label else value)
        else:
            choices.append(str(choice))
    blocks = [ContentBlock("text", q.question_text)]
    for part in q.metadata.get("question_parts") or []:
        if isinstance(part, dict):
            value = str(part.get("part_text") or part.get("text") or "").strip()
            if value:
                blocks.append(ContentBlock("text", value, metadata={"question_part": part}))
    return Question(
        question_id=question_id, question_type=q.question_type, answer_mode=q.answer_mode,
        question_content=blocks, answer_choices=choices, correct_answer=q.correct_answer,
        marks=q.marks, handwritten_upload_mode=q.handwritten_upload_mode,
        subject=q.subject, board=q.board, class_level=q.class_level,
        chapter=q.chapter, topic=q.topic, subtopic=q.subtopic,
        difficulty=q.difficulty, competency=q.competency, source=q.source,
        source_year=q.source_year, status="active",
    )

class ApprovedQuestionPublisher:
    """Publish only after explicit human approval and rights confirmation."""
    def __init__(self, storage, *, review_service: Optional[QuestionReviewService] = None):
        self.storage = storage
        self.review_service = review_service or QuestionReviewService()
    def approve_and_publish(self, candidate: IngestionCandidate, *, reviewer: str,
                            question_id: str, rights_confirmed: bool,
                            note: Optional[str] = None) -> tuple[Question, ReviewDecision]:
        decision = self.review_service.approve(
            candidate, reviewer=reviewer, rights_confirmed=rights_confirmed, note=note
        )
        question = candidate_to_question(candidate, question_id=question_id)
        self.storage.create_question(question, sync_to_secondary=True)
        return question, decision
