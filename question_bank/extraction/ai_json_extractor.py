"""External-AI JSON adapter for the canonical question-ingestion pipeline.

JSON is treated as a transport format produced by an external extractor
(Claude, Gemini, ChatGPT, etc.). Imported records are converted to the shared
RawQuestion contract and must continue through normalization, validation,
duplicate detection, review, and approval before production persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exam_platform.ingestion.models import RawQuestion, SourceDocument


class AIJSONExtractionError(ValueError):
    """Raised when an AI extraction payload cannot be safely imported."""


class AIJSONQuestionExtractor:
    schema_version = "1.0"
    extraction_method = "ai_json"

    def __init__(self, payload: dict | list | str | Path):
        self.payload = self._load(payload)

    @staticmethod
    def _load(payload: dict | list | str | Path) -> Any:
        if isinstance(payload, (str, Path)):
            path = Path(payload)
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    raise AIJSONExtractionError(f"Invalid JSON file: {path}") from exc
            try:
                return json.loads(str(payload))
            except json.JSONDecodeError as exc:
                raise AIJSONExtractionError(
                    "Input is neither a JSON file nor valid JSON."
                ) from exc
        return payload

    def _envelope(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if isinstance(self.payload, list):
            return {}, self.payload

        if not isinstance(self.payload, dict):
            raise AIJSONExtractionError(
                "Top-level JSON must be an object or an array."
            )

        questions = self.payload.get("questions")
        if not isinstance(questions, list):
            raise AIJSONExtractionError("JSON must contain a 'questions' array.")

        version = str(self.payload.get("schema_version", self.schema_version))
        if version != self.schema_version:
            raise AIJSONExtractionError(
                f"Unsupported schema_version {version!r}; "
                f"expected {self.schema_version!r}."
            )

        return self.payload, questions

    @staticmethod
    def _text(value: Any, field: str, required: bool = False) -> str:
        if value is None:
            if required:
                raise AIJSONExtractionError(
                    f"Question field '{field}' is required."
                )
            return ""
        if not isinstance(value, str):
            raise AIJSONExtractionError(
                f"Question field '{field}' must be a string."
            )
        return value.strip()

    @staticmethod
    def _options(value: Any) -> list[dict[str, str]]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise AIJSONExtractionError("'answer_choices' must be an array.")

        output: list[dict[str, str]] = []
        for index, item in enumerate(value):
            if isinstance(item, str):
                output.append({"label": chr(65 + index), "text": item.strip()})
            elif isinstance(item, dict):
                label = item.get("label")
                text = item.get("text")
                if not isinstance(label, str) or not isinstance(text, str):
                    raise AIJSONExtractionError(
                        "Each answer choice must contain string 'label' and 'text'."
                    )
                output.append({"label": label.strip(), "text": text.strip()})
            else:
                raise AIJSONExtractionError(
                    "Each answer choice must be a string or object."
                )
        return output

    def to_source_document(self) -> SourceDocument:
        envelope, _ = self._envelope()
        source = envelope.get("source") or {}
        if not isinstance(source, dict):
            raise AIJSONExtractionError("'source' must be an object.")

        metadata = envelope.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise AIJSONExtractionError("'metadata' must be an object.")

        return SourceDocument(
            source_id=str(
                source.get("source_id")
                or envelope.get("source_id")
                or "ai-json-import"
            ),
            source_type=str(source.get("source_type") or "ai_json"),
            name=source.get("name") or envelope.get("source_name"),
            url=source.get("url"),
            source_year=source.get("source_year") or source.get("year"),
            rights_status=str(source.get("rights_status") or "unknown"),
            metadata={
                **metadata,
                "extraction_method": self.extraction_method,
                "extraction_provider": envelope.get("extraction_provider"),
                "extraction_model": envelope.get("extraction_model"),
                "extraction_run_id": envelope.get("extraction_run_id"),
                "schema_version": self.schema_version,
            },
        )

    def extract(self) -> list[RawQuestion]:
        envelope, questions = self._envelope()
        source_id = self.to_source_document().source_id
        defaults = envelope.get("defaults") or {}
        if not isinstance(defaults, dict):
            raise AIJSONExtractionError("'defaults' must be an object.")

        output: list[RawQuestion] = []

        for index, item in enumerate(questions, 1):
            if not isinstance(item, dict):
                raise AIJSONExtractionError(
                    f"Question #{index} must be an object."
                )

            source = item.get("source") or item.get("source_details") or {}
            if not isinstance(source, dict):
                raise AIJSONExtractionError(
                    f"Question #{index} field 'source' must be an object."
                )

            extraction_warnings = item.get("extraction_warnings") or []
            if not isinstance(extraction_warnings, list):
                raise AIJSONExtractionError(
                    f"Question #{index} 'extraction_warnings' must be an array."
                )

            question_number = item.get("question_number")
            question_text = self._text(
                item.get("question_text") or item.get("text") or item.get("question"), "question_text", required=True
            )

            # Source numbering is provenance, not a canonical database ID.
            raw_question_id = f"ai-json-{index}"

            metadata = {
                **defaults,
                "question_number": question_number,
                "question_parts": item.get("question_parts") or item.get("parts") or [],
                "question_type": item.get("question_type")
                or item.get("type")
                or defaults.get("question_type"),
                "original_question_type": item.get("question_type") or item.get("type"),
                "answer_mode": item.get("answer_mode")
                or defaults.get("answer_mode"),
                "handwritten_upload_mode": item.get("handwritten_upload_mode")
                or defaults.get("handwritten_upload_mode", "none"),
                "subject": item.get("subject") or defaults.get("subject"),
                "board": item.get("board") or defaults.get("board"),
                "class_level": item.get("class_level")
                or item.get("class")
                or defaults.get("class_level"),
                "chapter": item.get("chapter") or defaults.get("chapter"),
                "topic": item.get("topic") or defaults.get("topic"),
                "subtopic": item.get("subtopic") or defaults.get("subtopic"),
                "difficulty": item.get("difficulty")
                or defaults.get("difficulty"),
                "competency": item.get("competency")
                or defaults.get("competency"),
                "source_page": item.get("source_page"),
                "source_pages": item.get("source_pages") or (
                    [item["source_page"]]
                    if isinstance(item.get("source_page"), int)
                    else []
                ),
                "source_question_number": item.get("source_question_number")
                or question_number,
                "source_occurrence_id": item.get("source_occurrence_id"),
                "source": source,\n                "source_label": source.get("label") or source.get("name"),\n                "source_details": source,\n                "solution": item.get("solution"),\n                "marking_scheme": item.get("marking_scheme"),\n                "syllabus_status": item.get("syllabus_status"),
                "assets": item.get("assets") or [],
                "diagram_reference": item.get("diagram_reference"),
                "extraction_confidence": item.get("extraction_confidence"),
                "extraction_warnings": extraction_warnings,
                # These fields are explicitly untrusted until reviewed.
                "verification_status": "PENDING",
            }

            output.append(
                RawQuestion(
                    raw_question_id=raw_question_id,
                    source_id=source_id,
                    raw_text=question_text,
                    raw_options=self._options(item.get("answer_choices") if item.get("answer_choices") is not None else item.get("options")),
                    raw_answer=self._text(
                        item.get("correct_answer"), "correct_answer"
                    )
                    or None,
                    raw_marks=item.get("marks"),
                    raw_assets=item.get("assets") or [],
                    source_reference=str(
                        item.get("source_reference")
                        or (
                            f"{source_id}:q{question_number}"
                            if question_number is not None
                            else f"{source_id}:item{index}"
                        )
                    ),
                    extraction_confidence=item.get("extraction_confidence"),
                    metadata=metadata,
                )
            )

        return output


def extract_ai_json_questions(
    payload: dict | list | str | Path,
) -> list[RawQuestion]:
    return AIJSONQuestionExtractor(payload).extract()
