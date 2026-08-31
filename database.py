"""MySQL database configuration and schema bootstrap for the assessment platform."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "edtech_assessment")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = os.getenv("DATABASE_URL") or f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

SCHEMA = [
"""CREATE TABLE IF NOT EXISTS students (student_id VARCHAR(32) PRIMARY KEY,name VARCHAR(150) NOT NULL,email VARCHAR(255) NOT NULL,phone VARCHAR(30),city VARCHAR(100),role VARCHAR(30) NOT NULL DEFAULT 'student',class_level INT,board VARCHAR(30),school VARCHAR(255),registration_date DATE,registration_source VARCHAR(100),status VARCHAR(30) NOT NULL DEFAULT 'active',created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,UNIQUE KEY uq_students_email(email)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS student_academic_profiles (profile_id BIGINT AUTO_INCREMENT PRIMARY KEY,student_id VARCHAR(32) NOT NULL,study_hours_per_week DECIMAL(5,2),preparation_level VARCHAR(100),current_study_methods_json TEXT,completed_chapters_json TEXT,current_chapter VARCHAR(150),most_difficult_chapter VARCHAR(150),improvement_areas_json TEXT,recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,INDEX idx_profile_student(student_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS student_chapter_status (id BIGINT AUTO_INCREMENT PRIMARY KEY,student_id VARCHAR(32) NOT NULL,chapter VARCHAR(150) NOT NULL,status VARCHAR(30) NOT NULL,board VARCHAR(30),class_level INT,recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,INDEX idx_chapter_student(student_id,chapter)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS student_improvement_areas (id BIGINT AUTO_INCREMENT PRIMARY KEY,student_id VARCHAR(32) NOT NULL,area VARCHAR(150) NOT NULL,priority INT NOT NULL DEFAULT 1,recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,INDEX idx_area_student(student_id,area)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS plans (plan_id VARCHAR(32) PRIMARY KEY,name VARCHAR(100) NOT NULL,description TEXT,amount_paise INT NOT NULL DEFAULT 0,billing_interval VARCHAR(30) NOT NULL DEFAULT 'one_time',active BOOLEAN NOT NULL DEFAULT TRUE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS subscriptions (subscription_id VARCHAR(40) PRIMARY KEY,student_id VARCHAR(32) NOT NULL,plan_id VARCHAR(32) NOT NULL,start_date DATE NOT NULL,end_date DATE,status VARCHAR(30) NOT NULL,FOREIGN KEY(student_id) REFERENCES students(student_id),FOREIGN KEY(plan_id) REFERENCES plans(plan_id),INDEX idx_subscription_student(student_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS payments (payment_id VARCHAR(40) PRIMARY KEY,student_id VARCHAR(32) NOT NULL,subscription_id VARCHAR(40),billing_period VARCHAR(20),amount_paise INT NOT NULL,currency VARCHAR(10) NOT NULL DEFAULT 'INR',payment_date DATETIME,payment_method VARCHAR(40),transaction_reference VARCHAR(150),status VARCHAR(30) NOT NULL,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(student_id),FOREIGN KEY(subscription_id) REFERENCES subscriptions(subscription_id),INDEX idx_payment_student_period(student_id,billing_period)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS tests (test_id VARCHAR(40) PRIMARY KEY,title VARCHAR(255) NOT NULL,subject VARCHAR(100) NOT NULL,class_level INT NOT NULL,board VARCHAR(30),test_date DATE,duration_minutes INT NOT NULL,total_marks DECIMAL(10,2) NOT NULL,test_type VARCHAR(50) NOT NULL DEFAULT 'weekly',status VARCHAR(30) NOT NULL,questions_json LONGTEXT NOT NULL,created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS questions (question_id VARCHAR(40) PRIMARY KEY,subject VARCHAR(100) NOT NULL DEFAULT 'Mathematics',board VARCHAR(30),class_level INT,chapter VARCHAR(150),topic VARCHAR(150),subtopic VARCHAR(150),question_type VARCHAR(40) NOT NULL,answer_mode VARCHAR(80) NOT NULL,difficulty VARCHAR(50),competency VARCHAR(100),question_content_json LONGTEXT NOT NULL,answer_choices_json LONGTEXT NOT NULL,correct_answer VARCHAR(255),marks DECIMAL(10,2) NOT NULL,handwritten_upload_mode VARCHAR(20) NOT NULL DEFAULT 'none',source VARCHAR(255),source_year INT,status VARCHAR(20) NOT NULL DEFAULT 'active',created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS test_questions (test_id VARCHAR(40) NOT NULL,question_id VARCHAR(40) NOT NULL,sequence_number INT NOT NULL,marks DECIMAL(10,2) NOT NULL,PRIMARY KEY(test_id,question_id),UNIQUE KEY uq_test_sequence(test_id,sequence_number),FOREIGN KEY(test_id) REFERENCES tests(test_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(question_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS attempts (attempt_id VARCHAR(50) PRIMARY KEY,student_id VARCHAR(32) NOT NULL,test_id VARCHAR(40) NOT NULL,started_at DATETIME NOT NULL,submitted_at DATETIME,status VARCHAR(30) NOT NULL,score DECIMAL(10,2),percentage DECIMAL(7,3),attempt_rate DECIMAL(7,3),accuracy DECIMAL(7,3),time_taken_seconds INT,FOREIGN KEY(student_id) REFERENCES students(student_id),FOREIGN KEY(test_id) REFERENCES tests(test_id),INDEX idx_attempt_student_test(student_id,test_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS responses (response_id VARCHAR(50) PRIMARY KEY,attempt_id VARCHAR(50) NOT NULL,question_id VARCHAR(40) NOT NULL,selected_answer VARCHAR(255),answer_status VARCHAR(30) NOT NULL,marks_awarded DECIMAL(10,2),is_correct BOOLEAN,answered_at DATETIME,UNIQUE KEY uq_attempt_question(attempt_id,question_id),FOREIGN KEY(attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(question_id),INDEX idx_response_attempt(attempt_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS answer_images (image_id VARCHAR(50) PRIMARY KEY,attempt_id VARCHAR(50) NOT NULL,question_id VARCHAR(40) NOT NULL,page_number INT NOT NULL,original_filename VARCHAR(255) NOT NULL,file_path TEXT NOT NULL,uploaded_at DATETIME NOT NULL,FOREIGN KEY(attempt_id) REFERENCES attempts(attempt_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(question_id),INDEX idx_image_attempt_question(attempt_id,question_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS evaluation_errors (evaluation_error_id BIGINT AUTO_INCREMENT PRIMARY KEY,response_id VARCHAR(50) NOT NULL,error_code VARCHAR(10) NOT NULL,comment TEXT,marks_lost DECIMAL(10,2),created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(response_id) REFERENCES responses(response_id) ON DELETE CASCADE,INDEX idx_error_response(response_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS question_history (student_id VARCHAR(32) NOT NULL,question_id VARCHAR(40) NOT NULL,attempt_count INT NOT NULL DEFAULT 0,correct_count INT NOT NULL DEFAULT 0,last_attempted_at DATETIME,last_correct_at DATETIME,last_marks_awarded DECIMAL(10,2),last_error_summary TEXT,PRIMARY KEY(student_id,question_id),FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,FOREIGN KEY(question_id) REFERENCES questions(question_id),INDEX idx_history_student(student_id,last_attempted_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]

def initialize_database():
    with engine.begin() as connection:
        for statement in SCHEMA:
            connection.execute(text(statement))
        # Lightweight migration for databases created before question status existed.
        try:
            connection.execute(text("ALTER TABLE questions ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"))
        except Exception as exc:
            if "Duplicate column" not in str(exc) and "1060" not in str(exc):
                raise
