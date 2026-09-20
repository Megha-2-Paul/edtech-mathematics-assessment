import pytest
from exam_platform.ingestion.models import IngestionStatus
from question_bank.extraction.ai_json_bulk_import import AIJSONBulkImporter, ApprovedQuestionPublisher, candidate_to_question

def payload():
    return {
        "schema_version": "1.0",
        "source": {"source_id": "CBSE-2025-MATHS", "name": "CBSE Class 10 Mathematics 2025",
                   "source_type": "pdf", "source_year": 2025, "rights_status": "review_required"},
        "extraction_provider": "external_ai", "extraction_model": "test-model",
        "defaults": {"subject": "Mathematics", "board": "CBSE", "class_level": 10,
                     "chapter": "Quadratic Equations"},
        "questions": [
            {"question_number": "1", "question_text": "Solve x^2 - 5x + 6 = 0.",
             "question_type": "saq", "answer_mode": "manual_written_answer",
             "handwritten_upload_mode": "required", "marks": 2, "source_page": 3},
            {"question_number": "2", "question_text": "Which is irrational?",
             "question_type": "mcq", "answer_mode": "option_selection",
             "answer_choices": [{"label": "A", "text": "1"}, {"label": "B", "text": "2"},
                                {"label": "C", "text": "√2"}, {"label": "D", "text": "4"}],
             "correct_answer": "C", "marks": 1, "source_page": 3},
        ],
    }

def test_bulk_import_runs_shared_pipeline():
    result = AIJSONBulkImporter().prepare(payload())
    assert result.total == 2
    assert result.review_required == 2
    assert all(c.status == IngestionStatus.REVIEW_REQUIRED.value for c in result.candidates)

def test_bulk_import_detects_batch_duplicates():
    data = payload()
    data["questions"].append(dict(data["questions"][0]))
    result = AIJSONBulkImporter().prepare(data)
    assert result.total == 3
    assert result.review_required == 2
    assert result.duplicates == 1
    assert result.candidates[-1].duplicate_of == "ai-json-1"

def test_candidate_maps_to_existing_question_model():
    candidate = AIJSONBulkImporter().prepare(payload()).candidates[1]
    question = candidate_to_question(candidate, question_id="Q9001")
    assert question.question_id == "Q9001"
    assert question.answer_choices[2] == "C) √2"
    assert question.correct_answer == "C"

def test_publisher_requires_rights_confirmation():
    candidate = AIJSONBulkImporter().prepare(payload()).candidates[0]
    class FakeStorage:
        def __init__(self): self.created = []
        def create_question(self, question): self.created.append(question)
    storage = FakeStorage()
    publisher = ApprovedQuestionPublisher(storage)
    with pytest.raises(ValueError, match="rights/licensing"):
        publisher.approve_and_publish(candidate, reviewer="Megha", question_id="Q9002", rights_confirmed=False)
    assert storage.created == []

def test_publisher_persists_only_after_approval():
    candidate = AIJSONBulkImporter().prepare(payload()).candidates[0]
    class FakeStorage:
        def __init__(self): self.created = []
        def create_question(self, question): self.created.append(question)
    storage = FakeStorage()
    question, decision = ApprovedQuestionPublisher(storage).approve_and_publish(
        candidate, reviewer="Megha", question_id="Q9003", rights_confirmed=True
    )
    assert decision.action == "approved"
    assert candidate.status == "approved"
    assert storage.created == [question]
