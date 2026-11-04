"""Eligibility rules for registered students accessing assessments."""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import engine
from .models import Student, Test


ACADEMIC_YEAR = "2026-27"


def is_test_eligible(student: Student | None, test: Test | None) -> bool:
    """Return True only when the student has a matching active enrollment."""
    if not student or not test:
        return False

    if (
        student.status != "active"
        or not student.board
        or student.class_level is None
        or not test.board
        or student.board != test.board
        or student.class_level != test.class_level
    ):
        return False

    try:
        with engine.connect() as db:
            row = db.execute(
                text("""
                    SELECT 1
                    FROM student_subject_enrollments e
                    JOIN subject_catalog sc
                      ON sc.subject_id = e.subject_id
                    WHERE e.student_id = :student
                      AND e.board = :board
                      AND e.class_level = :class
                      AND sc.subject_name = :subject
                      AND e.status = 'ACTIVE'
                      AND e.academic_year = :academic_year
                    LIMIT 1
                """),
                {
                    "student": student.student_id,
                    "board": test.board,
                    "class": test.class_level,
                    "subject": test.subject,
                    "academic_year": ACADEMIC_YEAR,
                },
            ).first()
            return row is not None
    except SQLAlchemyError:
        # A database failure must never grant assessment access.
        return False


def registration_required(student: Student | None) -> bool:
    """Return whether the student lacks a matching active subject enrollment."""
    if (
        not student
        or student.status != "active"
        or not student.board
        or student.class_level is None
        or not student.subject
    ):
        return True

    try:
        with engine.connect() as db:
            row = db.execute(
                text("""
                    SELECT 1
                    FROM student_subject_enrollments e
                    JOIN subject_catalog sc
                      ON sc.subject_id = e.subject_id
                    WHERE e.student_id = :student
                      AND e.board = :board
                      AND e.class_level = :class
                      AND sc.subject_name = :subject
                      AND e.status = 'ACTIVE'
                      AND e.academic_year = :academic_year
                    LIMIT 1
                """),
                {
                    "student": student.student_id,
                    "board": student.board,
                    "class": student.class_level,
                    "subject": student.subject,
                    "academic_year": ACADEMIC_YEAR,
                },
            ).first()
            return row is None
    except SQLAlchemyError:
        # Treat an unavailable enrollment check as incomplete registration.
        return True
