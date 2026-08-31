"""SQLite database setup for the assessment platform MVP."""

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
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    city TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    class_level INTEGER,
    board TEXT,
    school TEXT,
    registration_date TEXT,
    registration_source TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student_academic_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    study_hours_per_week TEXT,
    preparation_level TEXT,
    current_study_methods_json TEXT NOT NULL DEFAULT '[]',
    completed_chapters_json TEXT NOT NULL DEFAULT '[]',
    current_chapter TEXT,
    most_difficult_chapter TEXT,
    improvement_areas_json TEXT NOT NULL DEFAULT '[]',
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_chapter_status (
    student_id TEXT NOT NULL,
    chapter TEXT NOT NULL,
    status TEXT NOT NULL,
    board TEXT,
    class_level INTEGER,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, chapter, status),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_improvement_areas (
    student_id TEXT NOT NULL,
    area TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, area),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    amount_paise INTEGER NOT NULL DEFAULT 0,
    billing_interval TEXT NOT NULL DEFAULT 'one_time',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (plan_id) REFERENCES plans(plan_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    subscription_id TEXT,
    billing_period TEXT,
    amount_paise INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    payment_date TEXT,
    payment_method TEXT,
    transaction_reference TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(subscription_id)
);

CREATE TABLE IF NOT EXISTS tests (
    test_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    class_level INTEGER NOT NULL,
    board TEXT,
    test_date TEXT,
    duration_minutes INTEGER NOT NULL,
    total_marks INTEGER NOT NULL,
    test_type TEXT NOT NULL DEFAULT 'weekly',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL DEFAULT 'Mathematics',
    board TEXT,
    class_level INTEGER,
    chapter TEXT,
    topic TEXT,
    subtopic TEXT,
    question_type TEXT NOT NULL,
    answer_mode TEXT NOT NULL,
    difficulty TEXT,
    competency TEXT,
    question_content_json TEXT NOT NULL,
    answer_choices_json TEXT NOT NULL DEFAULT '[]',
    correct_answer TEXT,
    marks INTEGER NOT NULL,
    handwritten_upload_mode TEXT NOT NULL DEFAULT 'none',
    source TEXT,
    source_year INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_questions (
    test_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    marks INTEGER NOT NULL,
    PRIMARY KEY (test_id, question_id),
    UNIQUE (test_id, sequence_number),
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
    score REAL,
    percentage REAL,
    attempt_rate REAL,
    accuracy REAL,
    time_taken_seconds INTEGER,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (test_id) REFERENCES tests(test_id)
);

CREATE TABLE IF NOT EXISTS responses (
    response_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_answer TEXT,
    answer_status TEXT NOT NULL,
    marks_awarded REAL,
    is_correct INTEGER,
    answered_at TEXT,
    FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    UNIQUE (attempt_id, question_id)
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

CREATE TABLE IF NOT EXISTS evaluation_errors (
    evaluation_error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id TEXT NOT NULL,
    error_code TEXT NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(response_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_history (
    student_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    last_attempted_at TEXT,
    last_correct_at TEXT,
    last_marks_awarded REAL,
    last_error_summary TEXT,
    PRIMARY KEY (student_id, question_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_profiles_student ON student_academic_profiles(student_id);
CREATE INDEX IF NOT EXISTS idx_chapter_status_student ON student_chapter_status(student_id);
CREATE INDEX IF NOT EXISTS idx_improvement_student ON student_improvement_areas(student_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_student ON subscriptions(student_id);
CREATE INDEX IF NOT EXISTS idx_payments_student_period ON payments(student_id, billing_period);
CREATE INDEX IF NOT EXISTS idx_tests_date ON tests(test_date);
CREATE INDEX IF NOT EXISTS idx_test_questions_test ON test_questions(test_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_attempts_student ON attempts(student_id, started_at);
CREATE INDEX IF NOT EXISTS idx_attempts_student_test ON attempts(student_id, test_id);
CREATE INDEX IF NOT EXISTS idx_responses_attempt ON responses(attempt_id);
CREATE INDEX IF NOT EXISTS idx_responses_question ON responses(question_id);
CREATE INDEX IF NOT EXISTS idx_images_attempt_question ON answer_images(attempt_id, question_id);
CREATE INDEX IF NOT EXISTS idx_errors_response ON evaluation_errors(response_id);
CREATE INDEX IF NOT EXISTS idx_history_student ON question_history(student_id, last_attempted_at);
"""


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA)


initialize_database()
