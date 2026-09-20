"""JSON question-bank extractor.

Accepts AI-produced JSON that follows the canonical extraction contract and
converts it into RawQuestion objects for the existing ingestion pipeline.

This adapter deliberately does not write directly to the production database.
Imported questions go through the same normalization, validation, duplicate
detection and human-review path as PDF extraction.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

from exam_platform.ingestion.models import RawQuestion, SourceDocument


class JSONExtractionError(ValueError):
    """Raised when an extraction JSON payload is malformed or unsafe to import."""


class JSONQuestionExtractor:
    """Convert canonical question JSON into the shared RawQuestion contract."""

    schema_version = "1.0"
    extraction_method = "json_ai"

    def __init__(self, payload: Union[dict, list, str, Path]):
        self.payload = self._load(payload)

    @staticmethod
    def _load(payload: Union[dict, list, str, Path]) -> Any:
        if isinstance(payload, (str, Path)):
            path = Path(payload)
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise JSONExtractionError(f"Invalid JSON file: {path}") from exc
            try:
                return json.loads(str(payload))
            except json.JSONDecodeError as exc:
                raise JSONExtractionError("Input is neither a JSON file nor valid JSON.") from exc
        return payload

    def _envelope(self) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        if isinstance(self.payload, list):
            return {}, self.payload

        if not isinstance(self.payload, dict):
            raise JSONExtractionError("Top-level JSON must be an object or an array.")

        questions = self.payload.get("questions")
        if not isinstance(questions, list):
            raise JSONExtractionError("JSON must contain a 'questions' array.")

        version = self.payload.get("schema_version", self.schema_version)
        if str(version) != self.schema_version:
            raise JSONExtractionError(
                f"Unsupported schema_version {version!r}; expected {self.schema_version!r}."
            )

        return self.payload, questions

    @staticmethod
    def _text(value: Any, field: str, required: bool = False) -> str:
        if value is None:
            if required:
                raise JSONExtractionError(f"Question field '{field}' is required.")
            return ""
        if not isinstance(value, str):
            raise JSONExtractionError(f"Question field '{field}' must be a string.")
        return value.strip()

    @staticmethod
    def _options(value: Any) -> List[str]:
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise JSONExtractionError("'answer_choices' must be an array of strings.")
        return [item.strip() for item in value]

    def to_source_document(self) -> SourceDocument:
        envelope, _ = self._envelope()
        source = envelope.get("source") or {}
        if not isinstance(source, dict):
            raise JSONExtractionError("'source' must be an object.")

        return SourceDocument(
            source_id=str(source.get("source_id") or envelope.get("source_id") or "json-import"),
            source_type=str(source.get("source_type") or "api"),
            name=source.get("name") or envelope.get("source_name"),
            url=source.get("url"),
            source_year=source.get("source_year"),
            rights_status=str(source.get("rights_status") or "unknown"),
            metadata={
                **(envelope.get("metadata") or {}),
                "extraction_method": self.extraction_method,
                "extraction_provider": envelope.get("extraction_provider"),
                "extraction_model": envelope.get("extraction_model"),
                "extraction_run_id": envelope.get("extraction_run_id"),
                "schema_version": self.schema_version,
            },
        )

    def extract(self) -> List[RawQuestion]:
        envelope, questions = self._envelope()
        source_id = self.to_source_document().source_id
        defaults = envelope.get("defaults") or {}
        if not isinstance(defaults, dict):
            raise JSONExtractionError("'defaults' must be an object.")

        output: List[RawQuestion] = []
        for index, item in enumerate(questions, 1):
            if not isinstance(item, dict):
                raise JSONExtractionError(f"Question #{index} must be an object.")

            metadata = {
                **defaults,
                **(item.get("metadata") or {}),
                "question_number": item.get("question_number"),
                "question_type": item.get("question_type") or defaults.get("question_type"),
                "answer_mode": item.get("answer_mode") or defaults.get("answer_mode"),
                "handwritten_upload_mode": item.get("handwritten_upload_mode")
                or defaults.get("handwritten_upload_mode", "none"),
                "subject": item.get("subject") or defaults.get("subject"),
                "board": item.get("board") or defaults.get("board"),
                "class_level": item.get("class_level") or defaults.get("class_level"),
                "chapter": item.get("chapter") or defaults.get("chapter"),
                "topic": item.get("topic") or defaults.get("topic"),
                "subtopic": item.get("subtopic") or defaults.get("subtopic"),
                "difficulty": item.get("difficulty") or defaults.get("difficulty"),
                "competency": item.get("competency") or defaults.get("competency"),
                "source": item.get("source") or defaults.get("source"),
                "source_year": item.get("source_year") or defaults.get("source_year"),
                "extraction_confidence": item.get("extraction_confidence"),
                "extraction_warnings": item.get("extraction_warnings") or [],
                "verification_status": "PENDING",
            }

            question_text = self._text(item.get("question_text"), "question_text", required=True)
            question_id = str(
                item.get("raw_question_id")
                or item.get("question_id")
                or item.get("question_number")
                or f"json-{index}"
            )

            output.append(
                RawQuestion(
                    raw_question_id=question_id,
                    source_id=source_id,
                    raw_text=question_text,
                    raw_options=self._options(item.get("answer_choices")),
                    raw_answer=self._text(item.get("correct_answer"), "correct_answer") or None,
                    raw_marks=item.get("marks"),
                    raw_assets=item.get("assets") or [],
                    source_reference=str(
                        item.get("source_reference")
                        or item.get("source_page")
                        or item.get("source_question_number")
                        or question_id
                    ),
                    extraction_confidence=item.get("extraction_confidence"),
                    metadata=metadata,
                )
            )

        return output


def extract_json_questions(payload: Union[dict, list, str, Path]) -> List[RawQuestion]:
    return JSONQuestionExtractor(payload).extract()
