"""Eligibility rules for registered students accessing assessments."""

from .models import Student, Test

ALLOWED_MATH_SUBJECTS = {"Mathematics", "Applied Mathematics"}


def is_test_eligible(student: Student | None, test: Test | None) -> bool:
    """Return True only when board, class, and Mathematics track all match."""
    if not student or not test:
        return False
    if student.status != "active" or not student.subject:
        return False
    if student.board != test.board:
        return False
    if student.class_level != test.class_level:
        return False
    if student.subject not in ALLOWED_MATH_SUBJECTS:
        return False
    return student.subject == test.subject


def registration_required(student: Student | None) -> bool:
    """Return whether the current session lacks a completed Maths registration."""
    if not student:
        return True
    return not (
        student.status == "active"
        and student.class_level is not None
        and student.board in {"CBSE", "ICSE"}
        and student.subject in ALLOWED_MATH_SUBJECTS
    )
