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
    def test_schema_declares_all_core_tables(self):
        schema = "\n".join(SCHEMA)
        for table in EXPECTED_TABLES:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table} ", schema)

    def test_question_history_and_payment_schema_declare_expected_fields(self):
        schema = "\n".join(SCHEMA)
        history_sql = next(s for s in SCHEMA if "CREATE TABLE IF NOT EXISTS question_history " in s)
        payment_sql = next(s for s in SCHEMA if "CREATE TABLE IF NOT EXISTS payments " in s)
        for field in ("student_id", "question_id", "attempt_count", "correct_count"):
            self.assertIn(field, history_sql)
        for field in ("student_id", "billing_period", "amount_paise", "status"):
            self.assertIn(field, payment_sql)
        self.assertIn("question_history", schema)
        self.assertIn("payments", schema)


if __name__ == "__main__":
    unittest.main()
