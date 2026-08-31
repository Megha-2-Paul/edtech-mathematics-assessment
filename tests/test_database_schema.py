import sqlite3
import unittest

from database import SCHEMA


EXPECTED_TABLES = {
    "students",
    "student_academic_profiles",
    "student_chapter_status",
    "student_improvement_areas",
    "plans",
    "subscriptions",
    "payments",
    "tests",
    "questions",
    "test_questions",
    "attempts",
    "responses",
    "answer_images",
    "evaluation_errors",
    "question_history",
}


class DatabaseSchemaTests(unittest.TestCase):
    def test_schema_creates_all_core_tables(self):
        db = sqlite3.connect(":memory:")
        db.executescript(SCHEMA)
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        self.assertTrue(EXPECTED_TABLES.issubset(tables))
        db.close()

    def test_question_history_and_payment_tables_have_expected_fields(self):
        db = sqlite3.connect(":memory:")
        db.executescript(SCHEMA)
        history_columns = {row[1] for row in db.execute("PRAGMA table_info(question_history)")}
        payment_columns = {row[1] for row in db.execute("PRAGMA table_info(payments)")}
        self.assertTrue({"student_id", "question_id", "attempt_count", "correct_count"}.issubset(history_columns))
        self.assertTrue({"student_id", "billing_period", "amount_paise", "status"}.issubset(payment_columns))
        db.close()


if __name__ == "__main__":
    unittest.main()
