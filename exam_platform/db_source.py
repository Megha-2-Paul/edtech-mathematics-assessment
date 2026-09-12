"""Database-first persistence facade for the student and teacher application.

The legacy storage service remains available for compatibility with the extraction
review tooling. This facade makes MySQL the authoritative read source for the core
exam and teacher flows while delegating existing write operations to that service.
"""
import json
from datetime import datetime
from sqlalchemy import text
from database import engine
from .models import Test, Question, Student, Attempt, Response, AnswerImage, ContentBlock
from .storage import storage as legacy_storage


def _dt(value):
    if not value:
        return None
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def _question(row):
    blocks = [ContentBlock(**x) for x in json.loads(row["question_content_json"])]
    return Question(
        row["question_id"], row["question_type"], row["answer_mode"], blocks,
        json.loads(row["answer_choices_json"]), row["correct_answer"], row["marks"],
        row["handwritten_upload_mode"], row["subject"], row["board"], row["class_level"],
        row["chapter"], row["topic"], row["subtopic"], row["difficulty"],
        row["competency"], row["source"], row["source_year"], row["status"]
    )


def _test(row):
    questions = [r["question_id"] for r in row["question_rows"]] if "question_rows" in row else json.loads(row["questions_json"])
    return Test(row["test_id"], row["title"], row["subject"], row["class_level"],
                row["duration_minutes"], row["total_marks"], questions, row["status"],
                row["board"], str(row["test_date"]) if row["test_date"] else None, row["test_type"])


def _student(row):
    return Student(row["student_id"], row["name"], row["email"], row["phone"], row["city"],
                   row["role"], row["class_level"], row["board"], row["school"],
                   str(row["registration_date"]) if row["registration_date"] else None,
                   row["registration_source"], row["status"])


def _attempt(row):
    return Attempt(row["attempt_id"], row["student_id"], row["test_id"], _dt(row["started_at"]),
                   _dt(row["submitted_at"]), row["status"], row["score"], row["percentage"],
                   row["attempt_rate"], row["accuracy"], row["time_taken_seconds"])


def _response(row):
    return Response(row["response_id"], row["attempt_id"], row["question_id"],
                    row["selected_answer"], row["answer_status"], row["marks_awarded"],
                    bool(row["is_correct"]) if row["is_correct"] is not None else None,
                    _dt(row["answered_at"]))


def _image(row):
    return AnswerImage(row["image_id"], row["attempt_id"], row["question_id"],
                       row["page_number"], row["original_filename"], row["file_path"],
                       _dt(row["uploaded_at"]))


class DatabaseFirstStorage:
    """Read from MySQL on every core access; delegate compatible writes."""

    def __getattr__(self, name):
        return getattr(legacy_storage, name)

    @property
    def questions(self):
        with engine.connect() as db:
            return {r["question_id"]: _question(r) for r in db.execute(text("SELECT * FROM questions")).mappings()}

    @property
    def tests(self):
        with engine.connect() as db:
            rows = db.execute(text("SELECT * FROM tests")).mappings().all()
            result = {}
            for row in rows:
                links = db.execute(text("SELECT question_id FROM test_questions WHERE test_id=:id ORDER BY sequence_number"), {"id": row["test_id"]}).mappings().all()
                data = dict(row)
                data["question_rows"] = links
                result[row["test_id"]] = _test(data)
            return result

    @property
    def students(self):
        with engine.connect() as db:
            return {r["student_id"]: _student(r) for r in db.execute(text("SELECT * FROM students")).mappings()}

    @property
    def attempts(self):
        with engine.connect() as db:
            return {r["attempt_id"]: _attempt(r) for r in db.execute(text("SELECT * FROM attempts")).mappings()}

    @property
    def responses(self):
        with engine.connect() as db:
            return {r["response_id"]: _response(r) for r in db.execute(text("SELECT * FROM responses")).mappings()}

    @property
    def images(self):
        with engine.connect() as db:
            return {r["image_id"]: _image(r) for r in db.execute(text("SELECT * FROM answer_images")).mappings()}

    def get_test(self, test_id):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM tests WHERE test_id=:id"), {"id": test_id}).mappings().first()
            if not row:
                return None
            links = db.execute(text("SELECT question_id FROM test_questions WHERE test_id=:id ORDER BY sequence_number"), {"id": test_id}).mappings().all()
            data = dict(row)
            data["question_rows"] = links
            return _test(data)

    def get_question(self, qid):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM questions WHERE question_id=:id"), {"id": qid}).mappings().first()
            return _question(row) if row else None

    def get_questions(self, qids):
        if not qids:
            return []
        placeholders = ", ".join(f":id{i}" for i in range(len(qids)))
        params = {f"id{i}": qid for i, qid in enumerate(qids)}
        with engine.connect() as db:
            rows = db.execute(text(f"SELECT * FROM questions WHERE question_id IN ({placeholders})"), params).mappings().all()
        by_id = {r["question_id"]: _question(r) for r in rows}
        return [by_id[qid] for qid in qids if qid in by_id]

    def get_student(self, sid):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM students WHERE student_id=:id"), {"id": sid}).mappings().first()
            return _student(row) if row else None

    def get_attempt(self, aid):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM attempts WHERE attempt_id=:id"), {"id": aid}).mappings().first()
            return _attempt(row) if row else None

    def get_student_test_attempt(self, sid, tid):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM attempts WHERE student_id=:student AND test_id=:test ORDER BY started_at DESC LIMIT 1"), {"student": sid, "test": tid}).mappings().first()
            return _attempt(row) if row else None

    def get_response(self, aid, qid):
        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM responses WHERE attempt_id=:attempt AND question_id=:question"), {"attempt": aid, "question": qid}).mappings().first()
            return _response(row) if row else None

    def get_attempt_responses(self, aid):
        with engine.connect() as db:
            return [_response(r) for r in db.execute(text("SELECT * FROM responses WHERE attempt_id=:id ORDER BY response_id"), {"id": aid}).mappings()]

    def get_attempt_images(self, aid, qid):
        with engine.connect() as db:
            return [_image(r) for r in db.execute(text("SELECT * FROM answer_images WHERE attempt_id=:attempt AND question_id=:question ORDER BY page_number"), {"attempt": aid, "question": qid}).mappings()]

    def get_all_tests(self):
        return list(self.tests.values())

    def get_all_questions(self):
        return list(self.questions.values())


storage = DatabaseFirstStorage()
