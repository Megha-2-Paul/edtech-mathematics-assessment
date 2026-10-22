from io import BytesIO

import pytest
from pypdf import PdfReader

from exam_platform.report_pdf import render_report_pdf


def sample_report():
    return {
        "student_name": "Sample Student",
        "student_id": "STU-001",
        "test_title": "Class 12 Mathematics Assessment",
        "test_id": "TEST-001",
        "test_date": "01 Oct 2026",
        "class_level": 12,
        "board": "CBSE",
        "subject": "Mathematics",
        "duration_minutes": 180,
        "diagnosis": {
            "report_ready": True,
            "score": 62,
            "total_marks": 80,
            "percentage": 77.5,
            "attempted": 17,
            "unattempted": 3,
            "total_questions": 20,
            "attempt_rate": 85,
            "accuracy": 86.1,
            "attempted_available_marks": 72,
            "attempted_marks_awarded": 62,
            "unattempted_available_marks": 8,
            "marks_lost": 18,
            "chapter_analysis": [
                {"name": "Algebra", "marks": 18, "max_marks": 20, "percentage": 90, "attempted": 5, "evidence_status": "sufficient"},
                {"name": "Calculus", "marks": 15, "max_marks": 20, "percentage": 75, "attempted": 4, "evidence_status": "sufficient"},
                {"name": "Statistics", "marks": 7, "max_marks": 12, "percentage": 58.3, "attempted": 2, "evidence_status": "sufficient"},
            ],
            "strengths": [{"name": "Algebra", "percentage": 90}],
            "weaknesses": [{"name": "Statistics", "percentage": 58.3}],
            "error_counts": [
                {"code": "C01", "label": "Calculation", "count": 4},
                {"code": "C05", "label": "Incomplete steps", "count": 3},
            ],
            "recurring_errors": [
                {"code": "C01", "label": "Calculation", "prior_assessments": 1}
            ],
            "previous_attempt_count": 1,
            "previous_score": 59,
            "previous_percentage": 73.75,
            "marks_change": 3,
            "score_change": 3.75,
            "percentage_change": 3.75,
            "comparison_note": "Previous test had a different question mix; treat change as indicative.",
        },
        "recommendations": [
            {"title": "Check calculations", "action": "Practise 10 calculation-focused questions and verify intermediate steps."},
            {"title": "Review Statistics", "action": "Redo selected questions and explain the method."},
        ],
    }


def test_pdf_is_exactly_two_pages_and_contains_only_target_student():
    pdf = render_report_pdf(sample_report())
    assert isinstance(pdf, BytesIO)
    reader = PdfReader(pdf)
    assert len(reader.pages) == 2
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Sample Student" in text
    assert "STU-001" in text
    assert "Recorded error patterns" in text
    assert "Personalised next steps" in text
    assert "ANOTHER-STUDENT" not in text


def test_pdf_refuses_incomplete_report():
    report = sample_report()
    report["diagnosis"]["report_ready"] = False
    with pytest.raises(ValueError, match="before evaluation"):
        render_report_pdf(report)
