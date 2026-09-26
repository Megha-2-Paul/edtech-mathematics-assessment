import pytest

from exam_platform.ingestion.models import SourceDocument
from question_bank.extraction.ai_json_extractor import (
    AIJSONExtractionError,
    AIJSONQuestionExtractor,
)


def sample_payload():
    return {
        "schema_version": "1.0",
        "source": {
            "source_id": "cbse-2025-maths",
            "name": "CBSE Class 10 Mathematics 2025",
            "source_type": "pdf",
            "source_year": 2025,
        },
        "extraction_provider": "external_ai",
        "extraction_model": "test-model",
        "defaults": {
            "subject": "Mathematics",
            "board": "CBSE",
            "class_level": 10,
        },
        "questions": [
            {
                "question_number": "1",
                "question_text": "Find the HCF of 24 and 36.",
                "question_type": "vsaq",
                "marks": 1,
                "source_page": 2,
            },
            {
                "question_number": "2",
                "question_text": "Which is irrational?",
                "question_type": "mcq",
                "answer_choices": [
                    {"label": "A", "text": "1"},
                    {"label": "B", "text": "2"},
                    {"label": "C", "text": "√2"},
                    {"label": "D", "text": "4"},
                ],
                "correct_answer": "C",
                "marks": 1,
                "source_pages": [2],
                "question_parts": [],
            },
        ],
    }


def test_json_extractor_converts_batch_to_raw_questions():
    questions = AIJSONQuestionExtractor(sample_payload()).extract()

    assert len(questions) == 2
    assert questions[0].raw_text.startswith("Find the HCF")
    assert questions[1].raw_options[2] == {"label": "C", "text": "√2"}
    assert questions[1].metadata["board"] == "CBSE"
    assert questions[1].metadata["source_pages"] == [2]
    assert questions[1].metadata["verification_status"] == "PENDING"
    assert questions[1].raw_question_id == "ai-json-2"


def test_json_extractor_supports_canonical_provider_aliases():
    payload = sample_payload()
    payload["questions"] = [
        {
            "question_number": 7,
            "text": "Choose the correct value.",
            "type": "mcq",
            "options": ["1", "2", "3", "4"],
            "correct_answer": "C",
            "marks": 1,
            "class": 10,
            "page_number": 4,
        }
    ]

    question = AIJSONQuestionExtractor(payload).extract()[0]

    assert question.raw_text == "Choose the correct value."
    assert question.raw_options[2] == {"label": "C", "text": "3"}
    assert question.metadata["question_type"] == "mcq"
    assert question.metadata["class_level"] == 10
    assert question.metadata["source_page"] == 4


def test_json_extractor_builds_source_document():
    source = AIJSONQuestionExtractor(sample_payload()).to_source_document()

    assert isinstance(source, SourceDocument)
    assert source.source_id == "cbse-2025-maths"
    assert source.metadata["extraction_method"] == "ai_json"


def test_json_extractor_accepts_string_source_with_source_details():
    payload = sample_payload()
    payload["source"] = "PDF_EXTRACTED"
    payload["source_details"] = {
        "source_id": "icse-2026-maths",
        "file": "Improvia_ICSE_Class10_Maths.pdf",
        "year": 2026,
    }
    payload["questions"][0]["source"] = "PDF_EXTRACTED"
    payload["questions"][0]["source_details"] = {
        "file": "Improvia_ICSE_Class10_Maths.pdf",
        "page": 7,
        "year": 2026,
    }

    extractor = AIJSONQuestionExtractor(payload)
    source = extractor.to_source_document()
    question = extractor.extract()[0]

    assert source.source_type == "PDF_EXTRACTED"
    assert source.file_path == "Improvia_ICSE_Class10_Maths.pdf"
    assert source.source_year == 2026
    assert question.metadata["source_label"] == "PDF_EXTRACTED"
    assert question.metadata["source_file"] == "Improvia_ICSE_Class10_Maths.pdf"
    assert question.metadata["source_details"]["page"] == 7
    assert question.metadata["verification_status"] == "PENDING"


def test_json_extractor_accepts_source_file_at_envelope_level():
    payload = sample_payload()
    payload["source"] = "PDF_EXTRACTED"
    payload["source_file"] = "paper.pdf"

    source = AIJSONQuestionExtractor(payload).to_source_document()

    assert source.name == "paper.pdf"
    assert source.file_path == "paper.pdf"


def test_json_extractor_rejects_invalid_source_details():
    payload = sample_payload()
    payload["source"] = "PDF_EXTRACTED"
    payload["source_details"] = "not-an-object"

    with pytest.raises(AIJSONExtractionError):
        AIJSONQuestionExtractor(payload).to_source_document()


def test_json_extractor_rejects_missing_questions_array():
    with pytest.raises(AIJSONExtractionError):
        AIJSONQuestionExtractor({"schema_version": "1.0"}).extract()


def test_json_extractor_rejects_unsupported_schema_version():
    with pytest.raises(AIJSONExtractionError):
        AIJSONQuestionExtractor(
            {"schema_version": "9.0", "questions": []}
        ).extract()


def test_json_extractor_does_not_use_source_question_number_as_database_id():
    payload = sample_payload()
    payload["questions"][0]["question_number"] = "Q17(b)"

    question = AIJSONQuestionExtractor(payload).extract()[0]

    assert question.raw_question_id == "ai-json-1"
    assert question.metadata["source_question_number"] == "Q17(b)"
