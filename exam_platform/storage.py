import json
from datetime import datetime
from typing import List, Optional

from database import get_connection
from .models import Test, Question, Student, Attempt, Response, AnswerImage, ContentBlock


class SQLiteStorage:
    """Persistent SQLite storage while keeping the existing service interface."""

    def __init__(self):
        self.tests = {}
        self.questions = {}
        self.students = {}
        self.attempts = {}
        self.responses = {}
        self.images = {}
        self._load_cache()

    @staticmethod
    def _dt(value):
        return datetime.fromisoformat(value) if value else None

    def _load_cache(self):
        with get_connection() as db:
            for row in db.execute("SELECT * FROM tests"):
                self.tests[row["test_id"]] = Test(
                    row["test_id"], row["title"], row["subject"], row["class_level"],
                    row["duration_minutes"], row["total_marks"],
                    json.loads(row["questions_json"]), row["status"]
                )
            for row in db.execute("SELECT * FROM questions"):
                blocks = [ContentBlock(**item) for item in json.loads(row["question_content_json"])]
                self.questions[row["question_id"]] = Question(
                    row["question_id"], row["question_type"], row["answer_mode"], blocks,
                    json.loads(row["answer_choices_json"]), row["correct_answer"],
                    row["marks"], row["handwritten_upload_mode"]
                )
            for row in db.execute("SELECT * FROM students"):
                self.students[row["student_id"]] = Student(
                    row["student_id"], row["name"], row["email"], row["phone"]
                )
            for row in db.execute("SELECT * FROM attempts"):
                self.attempts[row["attempt_id"]] = Attempt(
                    row["attempt_id"], row["student_id"], row["test_id"],
                    self._dt(row["started_at"]), self._dt(row["submitted_at"]), row["status"]
                )
            for row in db.execute("SELECT * FROM responses"):
                self.responses[row["response_id"]] = Response(
                    row["response_id"], row["attempt_id"], row["question_id"],
                    row["selected_answer"], row["answer_status"]
                )
            for row in db.execute("SELECT * FROM answer_images"):
                self.images[row["image_id"]] = AnswerImage(
                    row["image_id"], row["attempt_id"], row["question_id"], row["page_number"],
                    row["original_filename"], row["file_path"], self._dt(row["uploaded_at"])
                )

    def create_test(self, test: Test) -> None:
        with get_connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO tests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (test.test_id, test.title, test.subject, test.class_level, test.duration_minutes,
                 test.total_marks, json.dumps(test.questions), test.status),
            )
            db.executemany(
                "INSERT OR IGNORE INTO test_questions VALUES (?, ?, ?, ?)",
                [(test.test_id, qid, i, self.questions[qid].marks)
                 for i, qid in enumerate(test.questions, 1) if qid in self.questions],
            )
        self.tests[test.test_id] = test

    def get_test(self, test_id: str) -> Optional[Test]:
        return self.tests.get(test_id)

    def create_question(self, question: Question) -> None:
        content = [
            {"type": c.type, "value": c.value, "asset_id": c.asset_id, "metadata": c.metadata}
            for c in question.question_content
        ]
        with get_connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO questions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (question.question_id, question.question_type, question.answer_mode,
                 json.dumps(content, ensure_ascii=False), json.dumps(question.answer_choices, ensure_ascii=False),
                 question.correct_answer, question.marks, question.handwritten_upload_mode),
            )
        self.questions[question.question_id] = question

    def get_question(self, question_id: str) -> Optional[Question]:
        return self.questions.get(question_id)

    def get_questions(self, question_ids: List[str]) -> List[Question]:
        return [self.questions[qid] for qid in question_ids if qid in self.questions]

    def create_student(self, student: Student) -> None:
        with get_connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?)",
                (student.student_id, student.name, student.email, student.phone),
            )
        self.students[student.student_id] = student

    def get_student(self, student_id: str) -> Optional[Student]:
        return self.students.get(student_id)

    def create_attempt(self, attempt: Attempt) -> None:
        with get_connection() as db:
            db.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?)",
                (attempt.attempt_id, attempt.student_id, attempt.test_id,
                 attempt.started_at.isoformat(),
                 attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                 attempt.status),
            )
        self.attempts[attempt.attempt_id] = attempt

    def get_attempt(self, attempt_id: str) -> Optional[Attempt]:
        return self.attempts.get(attempt_id)

    def get_student_test_attempt(self, student_id: str, test_id: str) -> Optional[Attempt]:
        attempts = [a for a in self.attempts.values() if a.student_id == student_id and a.test_id == test_id]
        return max(attempts, key=lambda a: a.started_at) if attempts else None

    def update_attempt(self, attempt: Attempt) -> None:
        with get_connection() as db:
            db.execute(
                "UPDATE attempts SET submitted_at=?, status=? WHERE attempt_id=?",
                (attempt.submitted_at.isoformat() if attempt.submitted_at else None,
                 attempt.status, attempt.attempt_id),
            )
        self.attempts[attempt.attempt_id] = attempt

    def create_response(self, response: Response) -> None:
        with get_connection() as db:
            db.execute(
                "INSERT INTO responses VALUES (?, ?, ?, ?, ?)",
                (response.response_id, response.attempt_id, response.question_id,
                 response.selected_answer, response.answer_status),
            )
        self.responses[response.response_id] = response

    def get_response(self, attempt_id: str, question_id: str) -> Optional[Response]:
        return next((r for r in self.responses.values()
                     if r.attempt_id == attempt_id and r.question_id == question_id), None)

    def get_attempt_responses(self, attempt_id: str) -> List[Response]:
        return [r for r in self.responses.values() if r.attempt_id == attempt_id]

    def update_response(self, response: Response) -> None:
        with get_connection() as db:
            db.execute(
                "UPDATE responses SET selected_answer=?, answer_status=? WHERE response_id=?",
                (response.selected_answer, response.answer_status, response.response_id),
            )
        self.responses[response.response_id] = response

    def create_image(self, image: AnswerImage) -> None:
        with get_connection() as db:
            db.execute(
                "INSERT INTO answer_images VALUES (?, ?, ?, ?, ?, ?, ?)",
                (image.image_id, image.attempt_id, image.question_id, image.page_number,
                 image.original_filename, image.file_path, image.uploaded_at.isoformat()),
            )
        self.images[image.image_id] = image

    def get_attempt_images(self, attempt_id: str, question_id: str) -> List[AnswerImage]:
        return sorted(
            [i for i in self.images.values()
             if i.attempt_id == attempt_id and i.question_id == question_id],
            key=lambda x: x.page_number,
        )

    def delete_image(self, image_id: str) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM answer_images WHERE image_id=?", (image_id,))
        self.images.pop(image_id, None)


storage = SQLiteStorage()
