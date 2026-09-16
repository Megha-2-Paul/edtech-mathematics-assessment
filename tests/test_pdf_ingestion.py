from pathlib import Path

import fitz

from exam_platform.ingestion.adapters.pdf import PDFAdapter, extract_pdf_questions
from exam_platform.ingestion.models import SourceDocument
from exam_platform.ingestion.pipeline import QuestionIngestionPipeline


def _make_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (50, 60),
        "1. Solve x^2 - 5x + 6 = 0 [2 marks]\n"
        "2. Which is the value of 2 + 3?\n"
        "(A) 4\n"
        "(B) 5\n"
        "(C) 6\n"
        "(D) 7\n",
    )
    document.save(path)
    document.close()


def test_pdf_adapter_extracts_numbered_questions_and_options(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path)

    source = SourceDocument(
        source_id="PDF001",
        source_type="pdf",
        name="Sample paper",
        file_path=str(pdf_path),
        source_year=2026,
        rights_status="test_fixture",
    )
    questions = PDFAdapter(source).ingest()

    assert len(questions) == 2
    assert questions[0].raw_text == "Solve x^2 - 5x + 6 = 0 [2 marks]"
    assert questions[0].raw_marks == 2.0
    assert questions[0].metadata["page_start"] == 1
    assert questions[0].metadata["page_end"] == 1
    assert questions[0].extraction_confidence is not None
    assert questions[1].raw_options == ["4", "5", "6", "7"]
    assert questions[1].metadata["question_type"] == "mcq"


def test_pdf_adapter_reports_scanned_pdf_as_ocr_required(tmp_path):
    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    source, questions = extract_pdf_questions(str(pdf_path), source_id="SCAN001")

    assert questions == []
    assert source.metadata["ocr_required"] is True


def test_pdf_output_can_enter_existing_ingestion_pipeline(tmp_path):
    pdf_path = tmp_path / "pipeline.pdf"
    _make_pdf(pdf_path)

    source = SourceDocument(
        source_id="PDF002",
        source_type="pdf",
        name="Pipeline fixture",
        file_path=str(pdf_path),
        rights_status="test_fixture",
        metadata={"board": "CBSE", "class_level": 10, "chapter": "Quadratic Equations"},
    )
    raw_questions = PDFAdapter(source).ingest()
    for raw in raw_questions:
        raw.metadata.update(
            {
                "board": "CBSE",
                "class_level": 10,
                "chapter": "Quadratic Equations",
            }
        )

    candidates = QuestionIngestionPipeline().prepare(raw_questions, source)

    assert len(candidates) == 2
    assert all(candidate.provenance["source_type"] == "pdf" for candidate in candidates)
    assert all(candidate.status == "review_required" for candidate in candidates)
