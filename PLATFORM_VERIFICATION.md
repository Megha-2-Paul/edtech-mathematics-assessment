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

The project should be treated as **pre-functional-testing MVP code**. No claim of production readiness should be made until the complete local test flow succeeds.
