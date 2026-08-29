import unittest

from question_model import (
    BOARD_CHOICES,
    COMPETENCY_CHOICES,
    DIFFICULTY_CHOICES,
    EXTRACTION_STATUS_CHOICES,
    QUESTION_TYPE_CHOICES,
    VALIDATION_STATUS_CHOICES,
    Question,
    validate_question,
)


class TestQuestionModel(unittest.TestCase):
    def make_valid_question(self, **overrides):
        data = {
            "question_id": "Q_000001",
            "board": "CBSE",
            "class_level": 12,
            "subject": "Mathematics",
            "chapter": "Applications of Derivatives",
            "topic": "Maxima and Minima",
            "subtopic": "Second derivative test",
            "question_type": "mcq",
            "difficulty": "moderate",
            "competency": "application",
            "marks": 1,
            "question_text": "The point where the tangent is parallel to the x-axis is:",
            "instructions": "Choose the correct option.",
            "options": [
                {"id": "A", "text": "(0, 0)"},
                {"id": "B", "text": "(1, 1)"},
                {"id": "C", "text": "(2, 4)"},
                {"id": "D", "text": "(3, 9)"},
            ],
            "correct_answer": "A",
            "solution": "Differentiate and solve.",
            "source_type": "pyq",
            "source_name": "Sample Board Paper",
            "source_year": 2024,
            "source_exam": "Board Exam",
            "source_page": 8,
            "source_question_number": "5",
            "image_assets": [],
            "subquestions": [],
            "internal_choices": [],
            "extraction_status": "normalized",
            "validation_status": "valid",
            "validation_notes": ["Good question"],
            "status": "active",
            "tags": ["cbse", "class12"],
            "created_at": "2026-08-30T00:00:00Z",
            "updated_at": "2026-08-30T00:00:00Z",
            "created_by": "admin",
        }
        data.update(overrides)
        return Question(**data)

    def test_valid_mcq_question(self):
        question = self.make_valid_question()
        result = validate_question(question)
        self.assertTrue(result.valid)
        self.assertEqual(result.errors, [])

    def test_invalid_question_id(self):
        question = self.make_valid_question(question_id="INVALID")
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("question_id" in issue.field for issue in result.issues))

    def test_class_level_must_be_10_to_12(self):
        question = self.make_valid_question(class_level=9)
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("class_level" in issue.field for issue in result.issues))

    def test_question_type_must_be_valid(self):
        question = self.make_valid_question(question_type="invalid_type")
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("question_type" in issue.field for issue in result.issues))

    def test_marks_must_be_positive_integer(self):
        question = self.make_valid_question(marks=0)
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("marks" in issue.field for issue in result.issues))

    def test_mcq_requires_options(self):
        question = self.make_valid_question(options=[])
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("options" in issue.field for issue in result.issues))

    def test_mcq_requires_unique_option_ids(self):
        question = self.make_valid_question(
            options=[
                {"id": "A", "text": "One"},
                {"id": "A", "text": "Two"},
            ]
        )
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("options" in issue.field for issue in result.issues))

    def test_mcq_requires_matching_correct_answer(self):
        question = self.make_valid_question(correct_answer="Z")
        result = validate_question(question)
        self.assertFalse(result.valid)
        self.assertTrue(any("correct_answer" in issue.field for issue in result.issues))

    def test_long_answer_question_without_mcq_data_is_allowed(self):
        question = self.make_valid_question(
            question_type="long_answer",
            options=None,
            correct_answer=None,
            validation_status="valid",
            marks=5,
            question_text="Solve the differential equation.",
        )
        result = validate_question(question)
        self.assertTrue(result.valid)

    def test_question_id_uniqueness_can_be_checked_with_seen_ids(self):
        q1 = self.make_valid_question(question_id="Q_000010")
        q2 = self.make_valid_question(question_id="Q_000010")
        result = validate_question(q1, seen_ids={"Q_000010"})
        self.assertFalse(result.valid)
        self.assertTrue(any("not unique" in issue.message for issue in result.issues))

    def test_question_model_to_dict_round_trip(self):
        question = self.make_valid_question()
        payload = question.to_dict()
        restored = Question.from_dict(payload)
        self.assertEqual(restored.question_id, question.question_id)
        self.assertEqual(restored.board, question.board)
        self.assertEqual(restored.marks, question.marks)


class TestQuestionConstants(unittest.TestCase):
    def test_enums_are_defined(self):
        self.assertTrue(BOARD_CHOICES)
        self.assertTrue(QUESTION_TYPE_CHOICES)
        self.assertTrue(DIFFICULTY_CHOICES)
        self.assertTrue(COMPETENCY_CHOICES)
        self.assertTrue(EXTRACTION_STATUS_CHOICES)
        self.assertTrue(VALIDATION_STATUS_CHOICES)


if __name__ == "__main__":
    unittest.main()
