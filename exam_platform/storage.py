import json
from datetime import datetime
from typing import List, Optional

from database import get_connection
from .models import Test, Question, Student, Attempt, Response, AnswerImage, ContentBlock


class SQLiteStorage:
    """Persistent SQLite storage for the assessment platform MVP."""

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
                    row["duration_minutes"], row["total_marks"], json.loads(row["questions_json"]),
                    row["status"], row["board"], row["test_date"], row["test_type"]
                )
            for row in db.execute("SELECT * FROM questions"):
                blocks = [ContentBlock(**item) for item in json.loads(row["question_content_json"])]
                self.questions[row["question_id"]] = Question(
                    row["question_id"], row["question_type"], row["answer_mode"], blocks,
                    json.loads(row["answer_choices_json"]), row["correct_answer"], row["marks"],
                    row["handwritten_upload_mode"], row["subject"], row["board"], row["class_level"],
                    row["chapter"], row["topic"], row["subtopic"], row["difficulty"],
                    row["competency"], row["source"], row["source_year"]
                )
            for row in db.execute("SELECT * FROM students"):
                self.students[row["student_id"]] = Student(
                    row["student_id"], row["name"], row["email"], row["phone"], row["city"],
                    row["role"], row["class_level"], row["board"], row["school"],
                    row["registration_date"], row["registration_source"], row["status"]
                )
            for row in db.execute("SELECT * FROM attempts"):
                self.attempts[row["attempt_id"]] = Attempt(
                    row["attempt_id"], row["student_id"], row["test_id"], self._dt(row["started_at"]),
                    self._dt(row["submitted_at"]), row["status"], row["score"], row["percentage"],
                    row["attempt_rate"], row["accuracy"], row["time_taken_seconds"]
                )
            for row in db.execute("SELECT * FROM responses"):
                self.responses[row["response_id"]] = Response(
                    row["response_id"], row["attempt_id"], row["question_id"], row["selected_answer"],
                    row["answer_status"], row["marks_awarded"],
                    bool(row["is_correct"]) if row["is_correct"] is not None else None,
                    self._dt(row["answered_at"])
                )
            for row in db.execute("SELECT * FROM answer_images"):
                self.images[row["image_id"]] = AnswerImage(
                    row["image_id"], row["attempt_id"], row["question_id"], row["page_number"],
                    row["original_filename"], row["file_path"], self._dt(row["uploaded_at"])
                )

    def create_test(self, test: Test) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT OR IGNORE INTO tests
                (test_id,title,subject,class_level,board,test_date,duration_minutes,total_marks,test_type,status,questions_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (test.test_id, test.title, test.subject, test.class_level, test.board, test.test_date,
                 test.duration_minutes, test.total_marks, test.test_type, test.status, json.dumps(test.questions)),
            )
            db.executemany(
                "INSERT OR IGNORE INTO test_questions (test_id,question_id,sequence_number,marks) VALUES (?,?,?,?)",
                [(test.test_id, qid, i, self.questions[qid].marks)
                 for i, qid in enumerate(test.questions, 1) if qid in self.questions],
            )
        self.tests[test.test_id] = test

    def get_test(self, test_id: str) -> Optional[Test]:
        return self.tests.get(test_id)

    def create_question(self, question: Question) -> None:
        content = [{"type": c.type, "value": c.value, "asset_id": c.asset_id, "metadata": c.metadata}
                   for c in question.question_content]
        with get_connection() as db:
            db.execute(
                """INSERT OR IGNORE INTO questions
                (question_id,subject,board,class_level,chapter,topic,subtopic,question_type,answer_mode,
                 difficulty,competency,question_content_json,answer_choices_json,correct_answer,marks,
                 handwritten_upload_mode,source,source_year)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (question.question_id, question.subject, question.board, question.class_level, question.chapter,
                 question.topic, question.subtopic, question.question_type, question.answer_mode,
                 question.difficulty, question.competency, json.dumps(content, ensure_ascii=False),
                 json.dumps(question.answer_choices, ensure_ascii=False), question.correct_answer, question.marks,
                 question.handwritten_upload_mode, question.source, question.source_year),
            )
        self.questions[question.question_id] = question

    def get_question(self, question_id: str) -> Optional[Question]:
        return self.questions.get(question_id)

    def get_questions(self, question_ids: List[str]) -> List[Question]:
        return [self.questions[qid] for qid in question_ids if qid in self.questions]

    def create_student(self, student: Student) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT OR IGNORE INTO students
                (student_id,name,email,phone,city,role,class_level,board,school,registration_date,registration_source,status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (student.student_id, student.name, student.email, student.phone, student.city, student.role,
                 student.class_level, student.board, student.school, student.registration_date,
                 student.registration_source, student.status),
            )
        self.students[student.student_id] = student

    def get_student(self, student_id: str) -> Optional[Student]:
        return self.students.get(student_id)

    def create_attempt(self, attempt: Attempt) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO attempts
                (attempt_id,student_id,test_id,started_at,submitted_at,status,score,percentage,attempt_rate,accuracy,time_taken_seconds)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (attempt.attempt_id, attempt.student_id, attempt.test_id, attempt.started_at.isoformat(),
                 attempt.submitted_at.isoformat() if attempt.submitted_at else None, attempt.status,
                 attempt.score, attempt.percentage, attempt.attempt_rate, attempt.accuracy,
                 attempt.time_taken_seconds),
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
                """UPDATE attempts SET submitted_at=?, status=?, score=?, percentage=?, attempt_rate=?,
                accuracy=?, time_taken_seconds=? WHERE attempt_id=?""",
                (attempt.submitted_at.isoformat() if attempt.submitted_at else None, attempt.status,
                 attempt.score, attempt.percentage, attempt.attempt_rate, attempt.accuracy,
                 attempt.time_taken_seconds, attempt.attempt_id),
            )
        self.attempts[attempt.attempt_id] = attempt

    def create_response(self, response: Response) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO responses
                (response_id,attempt_id,question_id,selected_answer,answer_status,marks_awarded,is_correct,answered_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (response.response_id, response.attempt_id, response.question_id, response.selected_answer,
                 response.answer_status, response.marks_awarded,
                 int(response.is_correct) if response.is_correct is not None else None,
                 response.answered_at.isoformat() if response.answered_at else None),
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
                "UPDATE responses SET selected_answer=?, answer_status=?, marks_awarded=?, is_correct=?, answered_at=? WHERE response_id=?",
                (response.selected_answer, response.answer_status, response.marks_awarded,
                 int(response.is_correct) if response.is_correct is not None else None,
                 response.answered_at.isoformat() if response.answered_at else None, response.response_id),
            )
        self.responses[response.response_id] = response

    def create_image(self, image: AnswerImage) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO answer_images
                (image_id,attempt_id,question_id,page_number,original_filename,file_path,uploaded_at)
                VALUES (?,?,?,?,?,?,?)""",
                (image.image_id, image.attempt_id, image.question_id, image.page_number,
                 image.original_filename, image.file_path, image.uploaded_at.isoformat()),
            )
        self.images[image.image_id] = image

    def get_attempt_images(self, attempt_id: str, question_id: str) -> List[AnswerImage]:
        return sorted([i for i in self.images.values()
                       if i.attempt_id == attempt_id and i.question_id == question_id],
                      key=lambda x: x.page_number)

    def delete_image(self, image_id: str) -> None:
        with get_connection() as db:
            db.execute("DELETE FROM answer_images WHERE image_id=?", (image_id,))
        self.images.pop(image_id, None)

    # Registration/profile data -------------------------------------------------
    def record_academic_profile(
        self, student_id: str, study_hours_per_week: Optional[str], preparation_level: Optional[str],
        study_methods: list, completed_chapters: list, current_chapter: Optional[str],
        most_difficult_chapter: Optional[str], improvement_areas: list,
    ) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO student_academic_profiles
                (student_id,study_hours_per_week,preparation_level,current_study_methods_json,
                 completed_chapters_json,current_chapter,most_difficult_chapter,improvement_areas_json)
                VALUES (?,?,?,?,?,?,?,?)""",
                (student_id, study_hours_per_week, preparation_level, json.dumps(study_methods, ensure_ascii=False),
                 json.dumps(completed_chapters, ensure_ascii=False), current_chapter, most_difficult_chapter,
                 json.dumps(improvement_areas, ensure_ascii=False)),
            )

    def record_chapter_status(self, student_id: str, chapter: str, status: str,
                              board: Optional[str] = None, class_level: Optional[int] = None) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT OR REPLACE INTO student_chapter_status
                (student_id,chapter,status,board,class_level,recorded_at)
                VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (student_id, chapter, status, board, class_level),
            )

    def record_improvement_area(self, student_id: str, area: str, priority: int = 1) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT OR REPLACE INTO student_improvement_areas
                (student_id,area,priority,recorded_at) VALUES (?,?,?,CURRENT_TIMESTAMP)""",
                (student_id, area, priority),
            )

    # Subscription/payment data -------------------------------------------------
    def create_plan(self, plan_id: str, name: str, description: str, amount_paise: int,
                    billing_interval: str = "monthly") -> None:
        with get_connection() as db:
            db.execute(
                """INSERT OR REPLACE INTO plans
                (plan_id,name,description,amount_paise,billing_interval,active)
                VALUES (?,?,?,?,?,1)""",
                (plan_id, name, description, amount_paise, billing_interval),
            )

    def create_subscription(self, subscription_id: str, student_id: str, plan_id: str,
                            start_date: str, end_date: Optional[str], status: str) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO subscriptions
                (subscription_id,student_id,plan_id,start_date,end_date,status)
                VALUES (?,?,?,?,?,?)""",
                (subscription_id, student_id, plan_id, start_date, end_date, status),
            )

    def record_payment(self, payment_id: str, student_id: str, amount_paise: int,
                       billing_period: Optional[str], status: str, subscription_id: Optional[str] = None,
                       payment_date: Optional[str] = None, payment_method: Optional[str] = None,
                       transaction_reference: Optional[str] = None) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO payments
                (payment_id,student_id,subscription_id,billing_period,amount_paise,currency,payment_date,
                 payment_method,transaction_reference,status)
                VALUES (?,?,?,?,?,'INR',?,?,?,?,?)""",
                (payment_id, student_id, subscription_id, billing_period, amount_paise, payment_date,
                 payment_method, transaction_reference, status),
            )

    def get_payment_for_period(self, student_id: str, billing_period: str):
        with get_connection() as db:
            return db.execute(
                """SELECT * FROM payments WHERE student_id=? AND billing_period=?
                ORDER BY created_at DESC LIMIT 1""", (student_id, billing_period)
            ).fetchone()

    # Question history ----------------------------------------------------------
    def record_question_history(self, student_id: str, question_id: str, correct: bool,
                                marks_awarded: Optional[float], attempted_at: str,
                                error_summary: Optional[str] = None) -> None:
        with get_connection() as db:
            db.execute(
                """INSERT INTO question_history
                (student_id,question_id,attempt_count,correct_count,last_attempted_at,last_correct_at,
                 last_marks_awarded,last_error_summary)
                VALUES (?,?,1,?,?,?,?,?)
                ON CONFLICT(student_id,question_id) DO UPDATE SET
                    attempt_count=attempt_count+1,
                    correct_count=correct_count+excluded.correct_count,
                    last_attempted_at=excluded.last_attempted_at,
                    last_correct_at=CASE WHEN excluded.last_correct_at IS NOT NULL THEN excluded.last_correct_at ELSE question_history.last_correct_at END,
                    last_marks_awarded=excluded.last_marks_awarded,
                    last_error_summary=excluded.last_error_summary""",
                (student_id, question_id, 1 if correct else 0, attempted_at if correct else None,
                 attempted_at, marks_awarded, error_summary),
            )

    def get_question_history(self, student_id: str, question_id: Optional[str] = None):
        with get_connection() as db:
            if question_id:
                return db.execute(
                    "SELECT * FROM question_history WHERE student_id=? AND question_id=?",
                    (student_id, question_id),
                ).fetchone()
            return db.execute(
                "SELECT * FROM question_history WHERE student_id=? ORDER BY last_attempted_at DESC",
                (student_id,),
            ).fetchall()


storage = SQLiteStorage()
