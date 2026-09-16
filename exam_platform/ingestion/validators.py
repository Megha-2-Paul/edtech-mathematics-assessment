"""Deterministic validation for normalized question candidates."""

from typing import Iterable, Optional

from .models import NormalizedQuestion, ValidationResult


ALLOWED_QUESTION_TYPES = {"mcq", "vsaq", "saq", "laq"}
ALLOWED_UPLOAD_MODES = {"none", "optional", "required"}
ALLOWED_DIFFICULTIES = {"Easy", "Moderate", "Difficult"}
ALLOWED_BOARDS = {"CBSE", "ICSE", "ISC"}


def _has_value(value: Optional[str]) -> bool:
    return bool(value and str(value).strip())


def validate_question(
    question: NormalizedQuestion,
    *,
    allowed_boards: Iterable[str] = ALLOWED_BOARDS,
) -> ValidationResult:
    """Validate fields that can be checked without an external curriculum service."""

    errors = []
    warnings = []
    allowed_boards = set(allowed_boards)

    if not _has_value(question.question_text):
        errors.append("Question text is required.")
    if not _has_value(question.subject):
        errors.append("Subject is required.")
    if not question.board:
        errors.append("Board is required.")
    elif question.board not in allowed_boards:
        errors.append(f"Unsupported board: {question.board}.")
    if not question.class_level:
        errors.append("Class level is required.")
    if not _has_value(question.chapter):
        errors.append("Chapter is required.")
    if question.question_type not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Unsupported question type: {question.question_type}.")
    if question.answer_mode == "":
        errors.append("Answer mode is required.")
    if question.marks is None or question.marks <= 0:
        errors.append("Marks must be greater than zero.")

    if question.handwritten_upload_mode not in ALLOWED_UPLOAD_MODES:
        errors.append(
            f"Unsupported handwritten upload mode: {question.handwritten_upload_mode}."
        )

    if question.difficulty and question.difficulty not in ALLOWED_DIFFICULTIES:
        warnings.append(f"Unrecognized difficulty label: {question.difficulty}.")

    if question.question_type == "mcq":
        if not question.answer_choices:
            errors.append("MCQ requires answer choices.")
        if not question.correct_answer:
            errors.append("MCQ requires a correct answer.")
        elif question.correct_answer.upper() not in {
            chr(65 + i) for i in range(len(question.answer_choices))
        }:
            errors.append("MCQ correct answer does not match an available option.")

    if question.question_type != "mcq" and question.answer_choices:
        warnings.append("Non-MCQ question contains answer choices; review before publishing.")

    if not question.correct_answer and question.question_type != "mcq":
        warnings.append("Subjective answer has not been supplied; human review is required.")

    if question.assets:
        for index, asset in enumerate(question.assets, 1):
            if not asset.get("path") and not asset.get("url") and not asset.get("value"):
                warnings.append(f"Asset {index} has no usable path, URL, or value.")

    return ValidationResult(
        is_valid=not errors,
        errors=errors,
        warnings=warnings,
        confidence=1.0 if not errors else 0.0,
    )
