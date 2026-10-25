"""Compare a Groq extraction candidate JSON file with a human-verified gold file.

This is an offline benchmark: it does not call Groq, modify the database, or
publish candidates. Gold JSON should use the same envelope/fields as the
candidate file and contain only manually verified source transcription.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


COMPARE_FIELDS = (
    "question_text",
    "question_parts",
    "answer_choices",
    "marks",
    "question_type",
    "source_page",
)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {type(exc).__name__}") from None
    if not isinstance(value, dict) or not isinstance(value.get("questions"), list):
        raise ValueError(f"{path} must contain an object with a questions array.")
    if any(not isinstance(q, dict) for q in value["questions"]):
        raise ValueError(f"Every question in {path} must be an object.")
    return value


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", value.strip()) if isinstance(value, str) else ""


def _normal(value: Any) -> Any:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, list):
        return [_normal(item) for item in value]
    if isinstance(value, dict):
        return {key: _normal(item) for key, item in sorted(value.items())}
    return value


def _question_key(question: dict[str, Any], index: int) -> str:
    number = question.get("question_number") or question.get("source_question_number")
    return f"number:{str(number).strip()}" if number is not None else f"index:{index}"


def benchmark(
    candidate: dict[str, Any],
    gold: dict[str, Any],
    *,
    review_minutes: float | None = None,
    reviewed_questions: int | None = None,
) -> dict[str, Any]:
    candidates = candidate["questions"]
    gold_questions = gold["questions"]
    gold_by_key = {_question_key(q, i): q for i, q in enumerate(gold_questions)}
    candidate_by_key = {_question_key(q, i): q for i, q in enumerate(candidates)}

    # Exact normalized question text is the conservative boundary match. This
    # intentionally does not treat mathematically equivalent expressions as equal.
    gold_texts = [_text(q.get("question_text")) for q in gold_questions if _text(q.get("question_text"))]
    candidate_texts = [_text(q.get("question_text")) for q in candidates if _text(q.get("question_text"))]
    remaining = list(gold_texts)
    exact_text_matches = 0
    for value in candidate_texts:
        if value in remaining:
            exact_text_matches += 1
            remaining.remove(value)

    aligned = [
        (candidate_by_key[key], gold_by_key[key])
        for key in candidate_by_key.keys() & gold_by_key.keys()
    ]
    field_accuracy = {}
    for field in COMPARE_FIELDS:
        if not aligned:
            field_accuracy[field] = {"correct": 0, "compared": 0, "accuracy": None}
            continue
        correct = sum(_normal(left.get(field)) == _normal(right.get(field)) for left, right in aligned)
        field_accuracy[field] = {
            "correct": correct,
            "compared": len(aligned),
            "accuracy": round(correct / len(aligned), 4),
        }

    invalid = []
    missing_marks = []
    missing_page = []
    for index, question in enumerate(candidates, 1):
        if not _text(question.get("question_text")):
            invalid.append({"index": index, "reason": "missing_question_text"})
        if not isinstance(question.get("source_page"), int) or question.get("source_page") < 1:
            missing_page.append(index)
        if question.get("marks") is None:
            missing_marks.append(index)

    precision = exact_text_matches / len(candidate_texts) if candidate_texts else 0.0
    recall = exact_text_matches / len(gold_texts) if gold_texts else 0.0
    result = {
        "candidate_count": len(candidates),
        "gold_count": len(gold_questions),
        "count_delta_candidate_minus_gold": len(candidates) - len(gold_questions),
        "exact_question_text_matches": exact_text_matches,
        "question_text_boundary_precision": round(precision, 4),
        "question_text_boundary_recall": round(recall, 4),
        "aligned_question_count": len(aligned),
        "field_accuracy": field_accuracy,
        "invalid_candidates": invalid,
        "missing_marks_question_indices": missing_marks,
        "missing_source_page_question_indices": missing_page,
        "interpretation": (
            "Text equality uses whitespace normalization only. Mathematical notation, "
            "question parts, options, marks, and page numbers require human review."
        ),
    }
    if review_minutes is not None:
        denominator = reviewed_questions if reviewed_questions is not None else len(candidates)
        result["human_review"] = {
            "minutes": review_minutes,
            "questions_reviewed": denominator,
            "minutes_per_reviewed_question": round(review_minutes / denominator, 4) if denominator else None,
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Groq extraction benchmark against human-verified gold JSON.")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("groq_extraction_benchmark.json"))
    parser.add_argument("--review-minutes", type=float)
    parser.add_argument("--reviewed-questions", type=int)
    args = parser.parse_args(argv)
    if args.review_minutes is not None and args.review_minutes < 0:
        parser.error("--review-minutes cannot be negative")
    if args.reviewed_questions is not None and args.reviewed_questions < 0:
        parser.error("--reviewed-questions cannot be negative")

    try:
        report = benchmark(
            _load(args.candidate),
            _load(args.gold),
            review_minutes=args.review_minutes,
            reviewed_questions=args.reviewed_questions,
        )
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote benchmark report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
