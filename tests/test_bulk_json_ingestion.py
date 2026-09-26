import json
from pathlib import Path

from question_bank.extraction.ai_json_bulk_import import AIJSONBulkImporter, stable_batch_id
from question_bank.extraction.ai_json_extractor import AIJSONQuestionExtractor

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_51_question_batch_is_a_regression_fixture():
    payload = load_fixture("icse_class10_51_question_regression.json")
    result = AIJSONBulkImporter(existing_questions=[]).prepare(payload)

    assert result.total == 51
    assert result.duplicates == 0
    assert result.invalid == 0
    assert result.review_required == 51

    candidates = result.candidates
    assert [c.question.metadata["source_question_number"] for c in candidates] == [
        q["question_id"] for q in payload["questions"]
    ]
    matched = sum(c.question.metadata.get("curriculum_mapping_status") == "MATCHED" for c in candidates)
    unresolved = sum(c.question.metadata.get("curriculum_mapping_status") == "UNRESOLVED" for c in candidates)
    ambiguous = sum(c.question.metadata.get("curriculum_mapping_status") == "AMBIGUOUS" for c in candidates)
    assert matched == 48
    assert unresolved == 3
    assert ambiguous == 0
    assert candidates[1].question.question_type == "mcq"
    assert candidates[1].question.metadata["original_question_type"] == "ASSERTION_REASON"


def test_varied_json_batch_normalizes_aliases_and_detects_duplicate():
    payload = load_fixture("varied_ai_json_batch.json")
    result = AIJSONBulkImporter(existing_questions=[]).prepare(payload)

    assert result.total == 8
    assert result.review_required == 6
    assert result.duplicates == 1
    assert result.validation_pending == 1
    assert result.invalid == 1

    questions = result.candidates
    assert questions[0].question.question_type == "mcq"
    assert questions[0].question.correct_answer == "B"
    assert questions[1].question.question_type == "vsaq"
    assert questions[2].question.question_type == "saq"
    assert questions[3].question.question_type == "laq"
    assert questions[4].question.metadata["original_question_type"] == "assertion-reason"
    assert questions[4].question.question_type == "mcq"
    assert questions[5].question.metadata["source_pages"] == [4] or questions[5].question.metadata["source_pages"] == []
    assert questions[6].status == "VALIDATION_PENDING"
    assert questions[7].status == "DUPLICATE"
    assert questions[7].duplicate_of == "ai-json-1"


def test_exact_repeat_batch_has_stable_id():
    payload = load_fixture("varied_ai_json_batch.json")
    assert stable_batch_id(payload) == stable_batch_id(json.loads(json.dumps(payload)))
    changed = json.loads(json.dumps(payload))
    changed["questions"][0]["marks"] = 2
    assert stable_batch_id(payload) != stable_batch_id(changed)


def test_extractor_accepts_top_level_question_array():
    payload = load_fixture("varied_ai_json_batch.json")["questions"][:1]
    questions = AIJSONQuestionExtractor(payload).extract()
    assert len(questions) == 1
    assert questions[0].raw_text.startswith("What is the GST")