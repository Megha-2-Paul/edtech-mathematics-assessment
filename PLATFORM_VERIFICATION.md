# Platform Verification

## Purpose

This document records what is implemented versus what still requires local testing or production hardening.

## Implemented foundation

- Flask student-facing exam platform
- MySQL persistence layer
- MCQ and subjective question workflow
- Predefined final-answer choices
- Configurable handwritten upload: none / optional / required
- Answer persistence during an attempt
- Countdown timer
- Submission confirmation
- Duplicate-submission prevention
- Teacher/admin question-bank workflow
- Teacher/admin test creation workflow
- Manual subjective evaluation
- Structured evaluation error codes
- Result and performance-report views
- Question-level and student-level history foundations
- Canonical question ingestion/provenance and solution storage
- Optional question-bank primary-to-secondary sync
- Canonical Mathematics + Applied Mathematics syllabus taxonomy

## Verified taxonomy/database deployment

Taxonomy version: `2026.27.4`

Both local MySQL and Aiven MySQL were dry-run validated and then independently populated.

Expected and verified counts in both databases:

| Table / item | Count |
|---|---:|
| Subjects | 2 |
| canonical_chapters | 88 |
| syllabus_units | 62 |
| syllabus_chapters | 133 |
| Applied Mathematics canonical chapters | 31 |
| Review-required units | 0 |
| Review-required mappings | 0 |

The taxonomy migration is additive. Existing questions were not modified.

## Requires local functional testing

The following must be verified against the real local environment and MySQL database:

1. Application startup.
2. Database connection and schema initialization.
3. Student/test listing.
4. Test instructions and attempt creation.
5. MCQ answer saving.
6. Subjective final-answer saving.
7. Optional handwritten image upload.
8. Required handwritten image validation.
9. Multiple image uploads where supported.
10. Image display and deletion.
11. Countdown and expiry behavior.
12. Submission confirmation.
13. Duplicate submission/retake prevention.
14. Teacher submission list.
15. Manual evaluation and error-code storage.
16. Score, percentage, attempt-rate and accuracy calculations.
17. Student result/report pages.
18. Historical data and comparison behavior.
19. Subject-aware assessment eligibility for Mathematics vs Applied Mathematics.

## Production hardening still required

Before public launch:

- Secure secrets/environment configuration
- Authentication and authorization hardening
- Server-authoritative timing
- Attempt locking
- Secure object/image storage
- File validation and upload limits
- HTTPS
- Rate limiting
- Database backups
- Error logging/monitoring
- Evaluation audit trail
- Secure report access
- Privacy and consent handling

## Current status

The project is at the **controlled functional-testing / pre-public-launch stage**.

The database/taxonomy foundation is deployed and verified, but the complete student registration → assessment → evaluation → diagnosis → report loop still needs end-to-end validation before public launch.
