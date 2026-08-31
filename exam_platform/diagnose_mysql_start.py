"""Development-only diagnostic for the MySQL-backed test-start failure.

Run from the project root with:
    python -m exam_platform.diagnose_mysql_start

This does not change application behavior or commit test attempts. It checks
whether the mock test's student/foreign-key prerequisites are present and
reports the exact database exception if an isolated attempt insert fails.
"""
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database import engine
from exam_platform.models import Attempt
from exam_platform.storage import storage


def main():
    print("--- MYSQL TEST-START DIAGNOSTIC ---")
    print("tests in cache:", list(storage.tests.keys()))
    print("students in cache:", list(storage.students.keys()))

    with engine.connect() as db:
        student_count = db.execute(text("SELECT COUNT(*) FROM students")).scalar()
        test_count = db.execute(text("SELECT COUNT(*) FROM tests")).scalar()
        print("students in MySQL:", student_count)
        print("tests in MySQL:", test_count)

        fk_rows = db.execute(text("""
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'attempts'
              AND REFERENCED_TABLE_NAME IS NOT NULL
        """)).mappings().all()
        print("attempt foreign keys:", [dict(r) for r in fk_rows])

    test = next(iter(storage.tests.values()), None)
    if not test:
        print("No test is loaded; cannot reproduce start-test insert.")
        return

    diagnostic_student_id = f"DIAG{uuid.uuid4().hex[:10].upper()}"
    attempt_id = f"DIAGATT{uuid.uuid4().hex[:10].upper()}"
    attempt = Attempt(
        attempt_id=attempt_id,
        student_id=diagnostic_student_id,
        test_id=test.test_id,
        started_at=datetime.now(),
    )

    print("diagnostic student_id:", diagnostic_student_id)
    print("diagnostic test_id:", test.test_id)
    print("attempt insert: starting")
    try:
        storage.create_attempt(attempt)
    except Exception as exc:
        print("EXACT_ERROR_TYPE:", type(exc).__name__)
        print("EXACT_ERROR:", exc)
        print("TRACEBACK:")
        traceback.print_exc()
        return

    print("attempt insert: succeeded")
    print("WARNING: diagnostic insert succeeded; inspect/delete the DIAG attempt if present.")


if __name__ == "__main__":
    main()
