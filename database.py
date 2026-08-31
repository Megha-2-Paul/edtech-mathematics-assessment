"""SQLite database setup for the exam platform MVP."""

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "exam_platform.sqlite3"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS tests (
    test_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    class_level INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL,
    total_marks INTEGER NOT NULL,
    questions_json TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    question_type TEXT NOT NULL,
    answer_mode TEXT NOT NULL,
    question_content_json TEXT NOT NULL,
    answer_choices_json TEXT NOT NULL,
    correct_answer TEXT,
    marks INTEGER NOT NULL,
    handwritten_upload_mode TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_questions (
    test_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    marks INTEGER NOT NULL,
    PRIMARY KEY (test_id, question_id),
    FOREIGN KEY (test_id) REFERENCES tests(test_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (test_id) REFERENCES tests(test_id)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_answer TEXT,
    answer_status TEXT NOT NULL,
    UNIQUE (attempt_id, question_id),
    FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
);

CREATE TABLE IF NOT EXISTS answer_images (
    image_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
);

CREATE INDEX IF NOT EXISTS idx_attempts_student_test
    ON attempts(student_id, test_id);
CREATE INDEX IF NOT EXISTS idx_responses_attempt
    ON responses(attempt_id);
CREATE INDEX IF NOT EXISTS idx_images_attempt_question
    ON answer_images(attempt_id, question_id);
"""


def get_connection() -> sqlite3.Connection:
    """Return a configured SQLite connection."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the MVP schema if it does not already exist."""
    with get_connection() as connection:
        connection.executescript(SCHEMA)


initialize_database()
