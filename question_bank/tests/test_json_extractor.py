import json

import pytest

from exam_platform.ingestion.models import SourceDocument
from question_bank.extraction.json_extractor import (
    JSONExtractionError,
    JSONQuestionExtractor,
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
            "chapter": "Real Numbers",
        },
        "questions": [
            {
                "question_number": "1",
                "question_text": "Find the HCF of 24 and 36.",
                "question_type": "vsaq",
                "marks": 1,
            },
            {
                "question_number": "2",
                "question_text": "Which is irrational?",
                "question_type": "mcq",
                "answer_choices": ["A", "B", "√2", "D"],
                "correct_answer": "C",
                "marks": 1,
            },
        ],
    }


def test_json_extractor_converts_batch_to_raw_questions():
    extractor = JSONQuestionExtractor(sample_payload())
    questions = extractor.extract()

    assert len(questions) == 2
    assert questions[0].raw_text.startswith("Find the HCF")
    assert questions[1].raw_options == ["A", "B", "√2", "D"]
    assert questions[1].metadata["board"] == "CBSE"
    assert questions[1].metadata["verification_status"] == "PENDING"


def test_json_extractor_builds_source_document():
    source = JSONQuestionExtractor(sample_payload()).to_source_document()

    assert isinstance(source, SourceDocument)
    assert source.source_id == "cbse-2025-maths"
    assert source.metadata["extraction_method"] == "json_ai"


def test_json_extractor_rejects_missing_questions_array():
    with pytest.raises(JSONExtractionError):
        JSONQuestionExtractor({"schema_version": "1.0"}).extract()


def test_json_extractor_rejects_unsupported_schema_version():
    with pytest.raises(JSONExtractionError):
        JSONQuestionExtractor({"schema_version": "9.0", "questions": []}).extract()
