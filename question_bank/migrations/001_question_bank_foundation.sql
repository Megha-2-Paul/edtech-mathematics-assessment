-- Question Bank foundation migration.
-- Safe to run against the existing MySQL database.
-- This keeps manual and extracted questions in one canonical bank while preserving provenance.

ALTER TABLE questions
    ADD COLUMN source_type VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    ADD COLUMN verification_status VARCHAR(30) NOT NULL DEFAULT 'VERIFIED',
    ADD COLUMN canonical_question_id VARCHAR(40) NULL,
    ADD INDEX idx_questions_source_type (source_type),
    ADD INDEX idx_questions_verification_status (verification_status),
    ADD INDEX idx_questions_canonical (canonical_question_id);

CREATE TABLE IF NOT EXISTS source_papers (
    source_id VARCHAR(60) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    board VARCHAR(30),
    class_level INT,
    subject VARCHAR(100),
    paper_year INT,
    paper_set VARCHAR(100),
    qp_code VARCHAR(100),
    file_path TEXT NOT NULL,
    page_count INT,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source_paper_metadata (board, class_level, subject, paper_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_occurrences (
    occurrence_id VARCHAR(60) PRIMARY KEY,
    question_id VARCHAR(40) NOT NULL,
    source_id VARCHAR(60) NOT NULL,
    original_question_number VARCHAR(50),
    original_label VARCHAR(50),
    page_start INT,
    page_end INT,
    bbox_json TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (source_id) REFERENCES source_papers(source_id),
    UNIQUE KEY uq_question_occurrence (question_id, source_id, original_question_number, original_label),
    INDEX idx_occurrence_source (source_id),
    INDEX idx_occurrence_question (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_groups (
    group_id VARCHAR(60) PRIMARY KEY,
    source_id VARCHAR(60),
    group_type VARCHAR(30) NOT NULL,
    context_content_json LONGTEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES source_papers(source_id),
    INDEX idx_question_group_source (source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_parts (
    part_id VARCHAR(60) PRIMARY KEY,
    group_id VARCHAR(60),
    parent_question_id VARCHAR(40),
    question_id VARCHAR(40) NOT NULL,
    part_label VARCHAR(50),
    is_choice BOOLEAN NOT NULL DEFAULT FALSE,
    choice_group VARCHAR(50),
    sequence_number INT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES question_groups(group_id),
    FOREIGN KEY (parent_question_id) REFERENCES questions(question_id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    INDEX idx_question_parts_group (group_id),
    INDEX idx_question_parts_parent (parent_question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_extraction_runs (
    run_id VARCHAR(60) PRIMARY KEY,
    source_id VARCHAR(60) NOT NULL,
    page_number INT,
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(150),
    prompt_version VARCHAR(50),
    preprocessing_version VARCHAR(50),
    status VARCHAR(30) NOT NULL DEFAULT 'started',
    input_usage BIGINT,
    output_usage BIGINT,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES source_papers(source_id),
    INDEX idx_extraction_runs_source (source_id),
    INDEX idx_extraction_runs_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_extraction_results (
    extraction_result_id VARCHAR(70) PRIMARY KEY,
    run_id VARCHAR(60) NOT NULL,
    question_id VARCHAR(40),
    page_number INT,
    raw_output LONGTEXT,
    normalized_output LONGTEXT,
    text_confidence DECIMAL(6,4),
    math_confidence DECIMAL(6,4),
    boundary_confidence DECIMAL(6,4),
    asset_association_confidence DECIMAL(6,4),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES question_extraction_runs(run_id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    INDEX idx_extraction_result_run (run_id),
    INDEX idx_extraction_result_question (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS question_verifications (
    verification_id VARCHAR(70) PRIMARY KEY,
    question_id VARCHAR(40) NOT NULL,
    extraction_result_id VARCHAR(70),
    status VARCHAR(30) NOT NULL,
    original_output LONGTEXT,
    corrected_output LONGTEXT,
    reviewer VARCHAR(150),
    comments TEXT,
    verified_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(question_id),
    FOREIGN KEY (extraction_result_id) REFERENCES question_extraction_results(extraction_result_id),
    INDEX idx_verification_question (question_id),
    INDEX idx_verification_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS extraction_jobs (
    job_id VARCHAR(70) PRIMARY KEY,
    source_id VARCHAR(60) NOT NULL,
    page_number INT,
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    attempt_count INT NOT NULL DEFAULT 0,
    provider VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT,
    FOREIGN KEY (source_id) REFERENCES source_papers(source_id),
    UNIQUE KEY uq_extraction_job_page (source_id, page_number),
    INDEX idx_extraction_jobs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS extraction_providers (
    provider_id VARCHAR(60) PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL,
    model_name VARCHAR(150),
    free_status VARCHAR(30) NOT NULL DEFAULT 'UNVERIFIED',
    daily_limit INT,
    monthly_limit INT,
    rpm_limit INT,
    tpm_limit BIGINT,
    requires_billing BOOLEAN NOT NULL DEFAULT FALSE,
    last_verified_at DATETIME,
    verification_source TEXT,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_provider_model (provider_name, model_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS extraction_feedback (
    feedback_id VARCHAR(70) PRIMARY KEY,
    extraction_result_id VARCHAR(70) NOT NULL,
    error_type VARCHAR(60),
    original_value LONGTEXT,
    corrected_value LONGTEXT,
    reviewer VARCHAR(150),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_result_id) REFERENCES question_extraction_results(extraction_result_id),
    INDEX idx_feedback_result (extraction_result_id),
    INDEX idx_feedback_error_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Assets are deliberately extensible: diagrams, tables, graphs, charts, figures, etc.
ALTER TABLE question_assets
    ADD COLUMN page_number INT NULL,
    ADD COLUMN bbox_json TEXT NULL,
    ADD COLUMN asset_role VARCHAR(50) NULL,
    ADD COLUMN source_asset_id VARCHAR(70) NULL,
    ADD INDEX idx_question_asset_page (question_id, page_number);
