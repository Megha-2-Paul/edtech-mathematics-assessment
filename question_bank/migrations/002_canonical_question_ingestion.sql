-- Canonical question ingestion v2.
-- Adds solution/marking persistence and ensures the canonical question
-- provenance fields exist on deployments that did not run the foundation migration.

CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id VARCHAR(100) PRIMARY KEY,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET @qb2_applied := (
    SELECT COUNT(*) FROM schema_migrations
    WHERE migration_id = '002_canonical_question_ingestion'
);

DELIMITER $$
CREATE PROCEDURE apply_canonical_question_ingestion()
BEGIN
    IF @qb2_applied = 0 THEN
        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'questions' AND COLUMN_NAME = 'source_type'
        ) THEN
            ALTER TABLE questions ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'manual';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'questions' AND COLUMN_NAME = 'verification_status'
        ) THEN
            ALTER TABLE questions ADD COLUMN verification_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'questions' AND COLUMN_NAME = 'canonical_question_id'
        ) THEN
            ALTER TABLE questions ADD COLUMN canonical_question_id VARCHAR(40) NULL;
        END IF;

        UPDATE questions
        SET canonical_question_id = question_id
        WHERE canonical_question_id IS NULL OR canonical_question_id = '';

        CREATE TABLE IF NOT EXISTS question_solutions (
            question_solution_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            question_id VARCHAR(40) NOT NULL,
            solution_content LONGTEXT,
            marking_scheme LONGTEXT,
            version INT NOT NULL DEFAULT 1,
            verified BOOLEAN NOT NULL DEFAULT FALSE,
            source_type VARCHAR(30) NOT NULL DEFAULT 'extracted',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uq_question_solution_version(question_id, version),
            FOREIGN KEY(question_id) REFERENCES questions(question_id) ON DELETE CASCADE,
            INDEX idx_question_solution_question(question_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        INSERT INTO schema_migrations(migration_id)
        VALUES ('002_canonical_question_ingestion');
    END IF;
END$$
DELIMITER ;

CALL apply_canonical_question_ingestion();
DROP PROCEDURE apply_canonical_question_ingestion;
