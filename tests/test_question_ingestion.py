from exam_platform.ingestion.adapters.manual import ManualAdapter
from exam_platform.ingestion.models import SourceDocument
from exam_platform.ingestion.pipeline import QuestionIngestionPipeline, question_fingerprint


def test_manual_adapter_and_pipeline_create_review_candidate():
    source = SourceDocument(
        source_id="SRC001",
        source_type="manual",
        name="Improvia original",
        rights_status="original",
    )
    adapter = ManualAdapter(source)
    raw = adapter.ingest(
        [
            {
                "raw_question_id": "SRC001-Q1",
                "raw_text": "Solve x^2 - 5x + 6 = 0",
                "raw_marks": 2,
                "metadata": {
                    "board": "CBSE",
                    "class_level": 10,
                    "chapter": "Quadratic Equations",
                    "question_type": "saq",
                    "difficulty": "Moderate",
                },
            }
        ]
    )

    candidates = QuestionIngestionPipeline().prepare(raw, source)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.status == "review_required"
    assert candidate.validation.is_valid is True
    assert candidate.provenance["source_id"] == "SRC001"


def test_existing_question_is_flagged_as_exact_duplicate():
    source = SourceDocument(
        source_id="SRC002",
        source_type="manual",
        name="Another source",
    )
    adapter = ManualAdapter(source)
    raw = adapter.ingest(
        [
            {
                "raw_text": "  Solve   x^2 - 5x + 6 = 0 ",
                "raw_marks": 2,
                "metadata": {
                    "board": "CBSE",
                    "class_level": 10,
                    "chapter": "Quadratic Equations",
                    "question_type": "saq",
                },
            }
        ]
    )

    existing = type(
        "ExistingQuestion",
        (),
        {
            "question_id": "Q0001",
            "question_content": [type("Block", (), {"value": "Solve x^2 - 5x + 6 = 0"})()],
            "question_type": "saq",
            "answer_mode": "final_answer_selection_and_handwritten_upload",
            "answer_choices": [],
            "correct_answer": None,
            "marks": 2,
            "handwritten_upload_mode": "none",
            "subject": "Mathematics",
            "board": "CBSE",
            "class_level": 10,
            "chapter": "Quadratic Equations",
            "topic": None,
            "subtopic": None,
            "difficulty": None,
            "competency": None,
            "source": "Existing",
            "source_year": None,
        },
    )()

    pipeline = QuestionIngestionPipeline(existing_questions=[existing])
    candidates = pipeline.prepare(raw, source)

    assert candidates[0].status == "duplicate"
    assert candidates[0].duplicate_of == "Q0001"
    assert question_fingerprint(pipeline.normalize(raw[0], source))
