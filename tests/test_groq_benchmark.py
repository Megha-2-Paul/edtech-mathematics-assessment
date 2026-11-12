import json

import pytest

from scripts.benchmark_groq_extraction import benchmark


def test_benchmark_reports_boundaries_fields_and_missing_provenance():
    candidate = {
        "questions": [
            {
                "question_number": "1",
                "question_text": "Solve   x + 2 = 5.",
                "question_parts": [{"part_text": "(a) Solve"}],
                "answer_choices": [],
                "marks": 2,
                "question_type": "saq",
                "source_page": 1,
            },
            {
                "question_number": "2",
                "question_text": "Find y.",
                "marks": None,
                "source_page": None,
            },
        ]
    }
    gold = {
        "questions": [
            {
                "question_number": "1",
                "question_text": "Solve x + 2 = 5.",
                "question_parts": [{"part_text": "(a) Solve"}],
                "answer_choices": [],
                "marks": 2,
                "question_type": "saq",
                "source_page": 1,
            },
            {
                "question_number": "2",
                "question_text": "Find y.",
                "marks": 3,
                "source_page": 2,
            },
        ]
    }

    report = benchmark(candidate, gold, review_minutes=6, reviewed_questions=2)

    assert report["candidate_count"] == 2
    assert report["exact_question_text_matches"] == 2
    assert report["question_text_boundary_precision"] == 1.0
    assert report["question_text_boundary_recall"] == 1.0
    assert report["field_accuracy"]["marks"]["accuracy"] == 0.5
    assert report["missing_marks_question_indices"] == [2]
    assert report["missing_source_page_question_indices"] == [2]
    assert report["human_review"]["minutes_per_reviewed_question"] == 3.0


def test_benchmark_handles_empty_candidate_and_gold_lists():
    report = benchmark({"questions": []}, {"questions": []})
    assert report["candidate_count"] == 0
    assert report["question_text_boundary_precision"] == 0.0
    assert report["question_text_boundary_recall"] == 0.0
    assert report["field_accuracy"]["marks"]["accuracy"] is None
