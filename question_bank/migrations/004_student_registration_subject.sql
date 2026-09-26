-- Add the Mathematics track captured during registration.
-- Existing students remain NULL until they are explicitly registered/reviewed.
ALTER TABLE students
    ADD COLUMN subject VARCHAR(100) NULL AFTER board;

CREATE INDEX idx_students_eligibility
    ON students (status, board, class_level, subject);
