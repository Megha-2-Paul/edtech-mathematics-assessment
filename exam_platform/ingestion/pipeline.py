"""Orchestration for source-agnostic question ingestion."""

import re
from typing import Dict, Iterable, List, Optional

from .curriculum import CanonicalTaxonomyResolver
from .models import (
    IngestionCandidate,
    IngestionStatus,
    NormalizedQuestion,
    RawQuestion,
    SourceDocument,
)
from .provenance import build_provenance
from .validators import validate_question


def normalize_text(value: str) -> str:
    """Normalize whitespace/case for deterministic duplicate checks."""
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def question_fingerprint(question: NormalizedQuestion) -> str:
    """Return a deterministic fingerprint without requiring an external service."""
    choices = "|".join(normalize_text(choice) for choice in question.answer_choices)
    return "||".join(
        [
            normalize_text(question.question_text),
            normalize_text(choices),
            normalize_text(question.correct_answer or ""),
            str(question.marks),
            normalize_text(question.board or ""),
            str(question.class_level or ""),
        ]
    )


class QuestionIngestionPipeline:
    """Convert extractor output into reviewable candidates.

    Publishing is intentionally explicit. The pipeline does not automatically insert
    a candidate into the production questions table.
    """

    def __init__(
        self,
        *,
        existing_questions: Optional[Iterable[object]] = None,
        taxonomy_resolver: Optional[CanonicalTaxonomyResolver] = None,
    ):
        self.existing_fingerprints: Dict[str, str] = {}
        self.taxonomy_resolver = taxonomy_resolver or CanonicalTaxonomyResolver()
        for question in existing_questions or []:
            normalized = self._from_existing_question(question)
            self.existing_fingerprints[question_fingerprint(normalized)] = question.question_id

    @staticmethod
    def _from_existing_question(question: object) -> NormalizedQuestion:
        text = ""
        if getattr(question, "question_content", None):
            text = str(question.question_content[0].value or "")
        return NormalizedQuestion(
            raw_question_id=getattr(question, "question_id", "existing"),
            question_type=getattr(question, "question_type", "mcq"),
            answer_mode=getattr(question, "answer_mode", "option_selection"),
            question_text=text,
            answer_choices=list(getattr(question, "answer_choices", []) or []),
            correct_answer=getattr(question, "correct_answer", None),
            marks=float(getattr(question, "marks", 1) or 1),
            handwritten_upload_mode=getattr(question, "handwritten_upload_mode", "none"),
            subject=getattr(question, "subject", "Mathematics"),
            board=getattr(question, "board", None),
            class_level=getattr(question, "class_level", None),
            chapter=getattr(question, "chapter", None),
            topic=getattr(question, "topic", None),
            subtopic=getattr(question, "subtopic", None),
            difficulty=getattr(question, "difficulty", None),
            competency=getattr(question, "competency", None),
            source=getattr(question, "source", None),
            source_year=getattr(question, "source_year", None),
            source_type=getattr(question, "source_type", "manual"),
        )

    @staticmethod
    def normalize(raw: RawQuestion, source: SourceDocument) -> NormalizedQuestion:
        metadata = dict(source.metadata)
        metadata.update(raw.metadata)
        question_type = str(metadata.get("question_type") or "saq").lower()
        answer_mode = str(
            metadata.get(
                "answer_mode",
                "option_selection" if question_type == "mcq" else "final_answer_selection_and_handwritten_upload",
            )
        )

        normalized_choices = []
        for choice in raw.raw_options:
            if isinstance(choice, dict):
                label = str(choice.get("label") or "").strip()
                text = str(choice.get("text") or choice.get("value") or "").strip()
                normalized_choices.append(f"{label}) {text}" if label else text)
            else:
                normalized_choices.append(str(choice))

        return NormalizedQuestion(
            raw_question_id=raw.raw_question_id,
            question_type=question_type,
            answer_mode=answer_mode,
            question_text=raw.raw_text,
            answer_choices=normalized_choices,
            correct_answer=raw.raw_answer,
            marks=float(raw.raw_marks or 1),
            handwritten_upload_mode=str(metadata.get("handwritten_upload_mode", "none")),
            subject=str(metadata.get("subject") or "Mathematics"),
            board=metadata.get("board"),
            class_level=metadata.get("class_level"),
            chapter=metadata.get("chapter"),
            topic=metadata.get("topic"),
            subtopic=metadata.get("subtopic"),
            difficulty=metadata.get("difficulty"),
            competency=metadata.get("competency"),
            source=source.name or source.url or source.source_id,
            source_year=source.source_year,
            source_type=source.source_type,
            assets=list(raw.raw_assets),
            metadata=metadata,
        )

    def prepare(
        self,
        raw_questions: Iterable[RawQuestion],
        source: SourceDocument,
    ) -> List[IngestionCandidate]:
        """Normalize, resolve curriculum, validate and flag deterministic duplicates."""
        candidates = []
        seen_in_batch: Dict[str, str] = {}

        for raw in raw_questions:
            normalized = self.normalize(raw, source)

            mapping = self.taxonomy_resolver.resolve(
                subject=normalized.subject,
                board=normalized.board,
                class_level=normalized.class_level,
                chapter=normalized.chapter,
            )
            normalized.metadata.update(
                {
                    "curriculum_mapping_status": mapping.status,
                    "original_chapter": mapping.original_chapter,
                    "canonical_chapter_id": mapping.canonical_chapter_id,
                    "canonical_chapter_name": mapping.canonical_chapter_name,
                    "syllabus_unit_id": mapping.syllabus_unit_id,
                    "syllabus_unit_name": mapping.syllabus_unit_name,
                    "curriculum_mapping_reason": mapping.reason,
                    "curriculum_mapping_candidates": list(mapping.candidates),
                    "taxonomy_version": self.taxonomy_resolver.data.get("taxonomy_version"),
                }
            )

            validation = validate_question(normalized)
            fingerprint = question_fingerprint(normalized)

            duplicate_of = self.existing_fingerprints.get(fingerprint)
            if not duplicate_of:
                duplicate_of = seen_in_batch.get(fingerprint)

            if duplicate_of:
                status = IngestionStatus.DUPLICATE.value
            elif validation.is_valid:
                status = IngestionStatus.REVIEW_REQUIRED.value
            else:
                status = IngestionStatus.VALIDATION_PENDING.value

            candidate = IngestionCandidate(
                question=normalized,
                status=status,
                validation=validation,
                duplicate_of=duplicate_of,
                provenance=build_provenance(
                    source,
                    source_reference=raw.source_reference,
                    extraction_method=source.metadata.get("extraction_method"),
                ),
            )
            candidates.append(candidate)
            seen_in_batch[fingerprint] = raw.raw_question_id

        return candidates

    @staticmethod
    def publishable(candidate: IngestionCandidate) -> bool:
        """Return whether a candidate is eligible for explicit human approval."""
        return (
            candidate.status == IngestionStatus.REVIEW_REQUIRED.value
            and candidate.validation is not None
            and candidate.validation.is_valid
            and not candidate.duplicate_of
            and candidate.question.metadata.get("curriculum_mapping_status") == CanonicalTaxonomyResolver.MATCHED
        )
