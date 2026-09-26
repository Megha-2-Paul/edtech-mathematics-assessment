"""Bulk import orchestration for external-AI question JSON."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Optional
import hashlib
import json
from exam_platform.ingestion.models import IngestionCandidate, IngestionStatus
from exam_platform.ingestion.pipeline import QuestionIngestionPipeline
from exam_platform.ingestion.curriculum import CanonicalTaxonomyResolver
from exam_platform.ingestion.review import QuestionReviewService, ReviewDecision
from exam_platform.models import Question
from exam_platform.ingestion.canonical import build_question_from_candidate, solution_payload
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

def stable_batch_id(payload: dict | list) -> str:
    """Return a deterministic ID for an exact-repeat JSON batch."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "JSON_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


class AIJSONBulkImporter:
    """Convert one external-AI JSON batch into shared review candidates."""
    def __init__(self, *, existing_questions: Optional[Iterable[object]] = None,
                 taxonomy_resolver: Optional[CanonicalTaxonomyResolver] = None):
        self.pipeline = QuestionIngestionPipeline(
            existing_questions=existing_questions,
            taxonomy_resolver=taxonomy_resolver or CanonicalTaxonomyResolver(),
        )
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
    return build_question_from_candidate(candidate, question_id=question_id)

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
        self.storage.create_question(question)
        return question, decision
