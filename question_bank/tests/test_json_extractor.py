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


def test_json_extractor_builds_source_document():
    source = AIJSONQuestionExtractor(sample_payload()).to_source_document()

    assert isinstance(source, SourceDocument)
    assert source.source_id == "cbse-2025-maths"
    assert source.metadata["extraction_method"] == "ai_json"


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
