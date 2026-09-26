-- Add the Mathematics track captured during registration.
-- Existing students remain NULL until they are explicitly registered/reviewed.
-- This migration is idempotent because database.py may already have bootstrapped the column.
SET @student_subject_column_exists := (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'students'
      AND column_name = 'subject'
);

SET @student_subject_sql := IF(
    @student_subject_column_exists = 0,
    'ALTER TABLE students ADD COLUMN subject VARCHAR(100) NULL AFTER board',
    'SELECT 1'
);

PREPARE student_subject_stmt FROM @student_subject_sql;
EXECUTE student_subject_stmt;
DEALLOCATE PREPARE student_subject_stmt;

SET @student_eligibility_index_exists := (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'students'
      AND index_name = 'idx_students_eligibility'
);

SET @student_eligibility_index_sql := IF(
    @student_eligibility_index_exists = 0,
    'CREATE INDEX idx_students_eligibility ON students (status, board, class_level, subject)',
    'SELECT 1'
);

PREPARE student_eligibility_index_stmt FROM @student_eligibility_index_sql;
EXECUTE student_eligibility_index_stmt;
DEALLOCATE PREPARE student_eligibility_index_stmt;
