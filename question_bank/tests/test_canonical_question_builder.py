from exam_platform.ingestion.canonical import build_question
from exam_platform.ingestion.models import NormalizedQuestion
from exam_platform.models import Question


def test_canonical_builder_preserves_core_fields_and_provenance():
    normalized = NormalizedQuestion(
        raw_question_id="ai-json-1",
        question_type="MCQ",
        answer_mode="option_selection",
        question_text="If x=2, what is x+3?",
        answer_choices=[{"label": "A", "text": "4"}, {"label": "B", "text": "5"}],
        correct_answer="B",
        marks=1,
        subject="Mathematics",
        board="ICSE",
        class_level=10,
        chapter="Algebra",
        source="ICSE 2025",
        source_year=2025,
        source_type="ai_json",
        metadata={"solution": "Substitute x=2.", "marking_scheme": "1 mark for B."},
    )

    q = build_question(normalized, question_id="Q9001")

    assert isinstance(q, Question)
    assert q.question_type == "mcq"
    assert q.answer_choices == ["A) 4", "B) 5"]
    assert q.correct_answer == "B"
    assert q.source_type == "ai_json"
    assert q.verification_status == "VERIFIED"
    assert q.canonical_question_id == "Q9001"


def test_unsupported_question_type_is_not_silently_changed():
    normalized = NormalizedQuestion(
        raw_question_id="x",
        question_type="case_study",
        answer_mode="multi_part",
        question_text="Case study",
        board="ICSE",
        class_level=10,
        chapter="Algebra",
    )

    try:
        build_question(normalized, question_id="Q9002")
    except ValueError as exc:
        assert "Unsupported question type" in str(exc)
    else:
        raise AssertionError("Unsupported question type was silently accepted")
