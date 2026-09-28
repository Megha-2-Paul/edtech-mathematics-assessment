"""Eligibility rules for registered students accessing assessments."""

from sqlalchemy import text
from database import engine
from .models import Student, Test



def is_test_eligible(student: Student | None, test: Test | None) -> bool:
    """Return True only when board, class, and Mathematics track all match."""
    if not student or not test:
        return False
    if student.status != "active" or not student.board or student.class_level is None or not test.board:
        return False
    if student.board != test.board or student.class_level != test.class_level:
        return False
    try:
        with engine.connect() as db:
            row = db.execute(text("""
                SELECT 1
                FROM student_subject_enrollments e
                JOIN subject_catalog sc ON sc.subject_id=e.subject_id
                WHERE e.student_id=:student AND e.board=:board AND e.class_level=:class
                  AND sc.subject_name=:subject AND e.status='ACTIVE'
                  AND e.academic_year='2026-27'
                LIMIT 1
            """), {"student":student.student_id,"board":test.board,"class":test.class_level,"subject":test.subject}).first()
            if row:
                return True
    except Exception:
        pass
    # Backward-compatible fallback for legacy records before migration 005.
    return student.subject == test.subject


def registration_required(student: Student | None) -> bool:
    """Return whether the current session lacks a completed Maths registration."""
    if not student:
        return True
    if student.status != "active" or student.class_level is None or not student.board:
        return True
    try:
        with engine.connect() as db:
            row = db.execute(text("""
                SELECT 1 FROM student_subject_enrollments
                WHERE student_id=:student AND status='ACTIVE' AND academic_year='2026-27'
                LIMIT 1
            """), {"student":student.student_id}).first()
            return row is None
    except Exception:
        return not (student.subject and student.board in {"CBSE","ICSE","ISC"})
