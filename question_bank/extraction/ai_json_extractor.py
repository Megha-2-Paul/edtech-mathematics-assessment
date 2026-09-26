from pathlib import Path
from typing import Any

from exam_platform.ingestion.models import RawQuestion, SourceDocument
from question_bank.extraction.extraction_contract import FIELD_ALIASES, EXTRACTION_SCHEMA_VERSION
from question_bank.extraction.normalization import normalize_chapter, normalize_mcq_answer, normalize_question_type


class AIJSONExtractionError(ValueError):
    """Raised when an AI extraction payload cannot be safely imported."""


class AIJSONQuestionExtractor:
    schema_version = EXTRACTION_SCHEMA_VERSION
    extraction_method = "ai_json"

    def __init__(self, payload: dict | list | str | Path):
        self.payload = self._load(payload)

    @staticmethod
    def _load(payload: dict | list | str | Path) -> Any:
        import json
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
                raise AIJSONExtractionError("Input is neither a JSON file nor valid JSON.") from exc
        return payload

    @staticmethod
    def _first(mapping: dict[str, Any], canonical: str, default: Any = None) -> Any:
        for key in FIELD_ALIASES.get(canonical, (canonical,)):
            value = mapping.get(key)
            if value is not None:
                return value
        return default

    def _envelope(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if isinstance(self.payload, list):
            return {}, self.payload
        if not isinstance(self.payload, dict):
            raise AIJSONExtractionError("Top-level JSON must be an object or an array.")
        questions = self.payload.get("questions")
        if not isinstance(questions, list):
            raise AIJSONExtractionError("JSON must contain a 'questions' array.")
        version = str(self.payload.get("schema_version", self.schema_version))
        if version != self.schema_version:
            raise AIJSONExtractionError(
                f"Unsupported schema_version {version!r}; expected {self.schema_version!r}."
            )
        return self.payload, questions

    @staticmethod
    def _text(value: Any, field: str, required: bool = False) -> str:
        if value is None:
            if required:
                raise AIJSONExtractionError(f"Question field '{field}' is required.")
            return ""
        if not isinstance(value, str):
            raise AIJSONExtractionError(f"Question field '{field}' must be a string.")
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
                label, text = item.get("label"), item.get("text")
                if not isinstance(label, str) or not isinstance(text, str):
                    raise AIJSONExtractionError(
                        "Each answer choice must contain string 'label' and 'text'."
                    )
                output.append({"label": label.strip(), "text": text.strip()})
            else:
                raise AIJSONExtractionError("Each answer choice must be a string or object.")
        return output

    @staticmethod
    def _source_object(
        value: Any, *, details: Any = None, field_name: str = "source"
    ) -> dict[str, Any]:
        """Normalize structured source and legacy string+details representations."""
        if value is None:
            value = {}
        if isinstance(value, dict):
            source = dict(value)
        elif isinstance(value, str):
            source = {"source_type": value.strip()} if value.strip() else {}
        else:
            raise AIJSONExtractionError(f"'{field_name}' must be an object or string.")
        if details is not None:
            if not isinstance(details, dict):
                raise AIJSONExtractionError(f"'{field_name}_details' must be an object.")
            source = {**source, **details}
        return source

    def to_source_document(self) -> SourceDocument:
        envelope, _ = self._envelope()
        source = self._source_object(
            envelope.get("source"), details=envelope.get("source_details")
        )
        metadata = envelope.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise AIJSONExtractionError("'metadata' must be an object.")

        source_file = self._first(source, "source_file") or envelope.get("source_file") or metadata.get("source_file")
        source_name = (
            source.get("name")
            or source.get("source_name")
            or envelope.get("source_name")
            or metadata.get("source_name")
            or source_file
        )

        return SourceDocument(
            source_id=str(
                source.get("source_id")
                or envelope.get("source_id")
                or "ai-json-import"
            ),
            source_type=str(source.get("source_type") or "ai_json"),
            name=source_name,
            url=source.get("url"),
            file_path=source_file,
            source_year=source.get("source_year") or source.get("year"),
            rights_status=str(source.get("rights_status") or "unknown"),
            metadata={
                **metadata,
                "source_label": source.get("label")
                or source.get("source_label")
                or source.get("source_type"),
                "source_details": source,
                "extraction_method": self.extraction_method,
                "extraction_provider": self._first(envelope, "extraction_provider"),
                "extraction_model": self._first(envelope, "extraction_model"),
                "extraction_run_id": self._first(envelope, "extraction_run_id"),
                "schema_version": self.schema_version,
            },
        )

    def extract(self) -> list[RawQuestion]:
        envelope, questions = self._envelope()
        source_document = self.to_source_document()
        source_id = source_document.source_id
        metadata_defaults = envelope.get("metadata") or {}
        if not isinstance(metadata_defaults, dict):
            raise AIJSONExtractionError("'metadata' must be an object.")
        defaults = {**metadata_defaults, **(envelope.get("defaults") or {})}
        if defaults.get("class_level") is None and defaults.get("class") is not None:
            defaults["class_level"] = defaults["class"]
        if not isinstance(defaults, dict):
            raise AIJSONExtractionError("'defaults' must be an object.")

        output: list[RawQuestion] = []
        for index, item in enumerate(questions, 1):
            if not isinstance(item, dict):
                raise AIJSONExtractionError(f"Question #{index} must be an object.")

            source = self._source_object(
                item.get("source"),
                details=item.get("source_details"),
                field_name=f"Question #{index} source",
            )
            if not source:
                source = dict(source_document.metadata.get("source_details") or {})

            extraction_warnings = item.get("extraction_warnings") or []
            if not isinstance(extraction_warnings, list):
                raise AIJSONExtractionError(
                    f"Question #{index} 'extraction_warnings' must be an array."
                )

            question_number = item.get("question_number") or item.get("question_id")
            question_text = self._text(
                self._first(item, "question_text"), "question_text", required=True
            )
            raw_question_id = f"ai-json-{index}"

            source_file = self._first(source, "source_file") or source_document.file_path
            source_page = self._first(item, "source_page")
            source_pages = self._first(item, "source_pages")
            if source_pages is None:
                source_pages = [source_page] if isinstance(source_page, int) else []

            original_question_type = self._first(item, "question_type", defaults.get("question_type"))
            question_type, type_normalization = normalize_question_type(original_question_type)
            question_parts = self._first(
                item, "question_parts", defaults.get("question_parts")
            ) or []

            original_chapter = item.get("chapter") or defaults.get("chapter")
            normalized_chapter, chapter_normalization = normalize_chapter(
                original_chapter, item.get("topic") or defaults.get("topic")
            )
            raw_options = self._options(self._first(item, "answer_choices"))
            normalized_answer = self._text(item.get("correct_answer"), "correct_answer") or None
            if question_type == "mcq":
                normalized_answer, answer_normalization = normalize_mcq_answer(
                    normalized_answer, raw_options
                )
            else:
                answer_normalization = "not_applicable"

            metadata = {
                **defaults,
                "question_number": question_number,
                "question_parts": question_parts,
                "question_type": question_type,
                "original_question_type": original_question_type,
                "question_type_normalization": type_normalization,
                "answer_normalization": answer_normalization,
                "chapter_normalization": chapter_normalization,
                "answer_mode": item.get("answer_mode") or defaults.get("answer_mode"),
                "handwritten_upload_mode": item.get("handwritten_upload_mode")
                or defaults.get("handwritten_upload_mode", "none"),
                "subject": item.get("subject") or defaults.get("subject"),
                "board": item.get("board") or defaults.get("board"),
                "class_level": self._first(item, "class_level", defaults.get("class_level")),
                "chapter": normalized_chapter,
                "topic": item.get("topic") or defaults.get("topic"),
                "subtopic": item.get("subtopic") or defaults.get("subtopic"),
                "difficulty": item.get("difficulty") or defaults.get("difficulty"),
                "competency": item.get("competency") or defaults.get("competency"),
                "source_page": source_page,
                "source_pages": source_pages,
                "source_question_number": item.get("source_question_number") or question_number,
                "source_occurrence_id": item.get("source_occurrence_id"),
                "source": source,
                "source_label": source.get("label")
                or source.get("source_label")
                or source.get("source_type"),
                "source_details": source,
                "source_file": source_file,
                "solution": item.get("solution"),
                "marking_scheme": item.get("marking_scheme"),
                "syllabus_status": item.get("syllabus_status"),
                "assets": item.get("assets") or [],
                "diagram_reference": item.get("diagram_reference"),
                "extraction_confidence": item.get("extraction_confidence"),
                "extraction_warnings": extraction_warnings,
                "verification_status": "PENDING",
            }

            output.append(
                RawQuestion(
                    raw_question_id=raw_question_id,
                    source_id=source_id,
                    raw_text=question_text,
                    raw_options=raw_options,
                    raw_answer=normalized_answer,
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


def extract_ai_json_questions(payload: dict | list | str | Path) -> list[RawQuestion]:
    return AIJSONQuestionExtractor(payload).extract()
