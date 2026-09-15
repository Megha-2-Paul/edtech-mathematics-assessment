-- Adds the per-test live webcam monitoring setting.
--
-- Values:
--   off      = no webcam monitoring
--   optional = student may allow camera monitoring
--   required = camera must be available before the exam can start
--
-- Monitoring is live-only in this version. No video recording/storage is implied.

ALTER TABLE tests
    ADD COLUMN monitoring_mode VARCHAR(20) NOT NULL DEFAULT 'off';

ALTER TABLE tests
    ADD CONSTRAINT chk_tests_monitoring_mode
    CHECK (monitoring_mode IN ('off', 'optional', 'required'));
