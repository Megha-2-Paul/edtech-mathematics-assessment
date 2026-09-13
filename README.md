# Mathematics Assessment & Improvement System

A low-cost assessment platform for CBSE/ICSE Mathematics (initially Classes 10–12) focused on one question:

> **Why is a student losing marks, and what should they improve next?**

This is not intended to be a generic mock-test marketplace. The product loop is:

**Test → Submission → Evaluation → Diagnosis → Report → Student Profile → Recommended Focus → Next Test → Progress**

## Current MVP

- Flask-based student-facing exam website
- MCQ and subjective questions
- Subjective final-answer selection plus configurable handwritten-work upload
- Automatic answer persistence during an attempt
- Countdown timer and submission confirmation
- Duplicate-submission prevention
- Teacher/admin question-bank management
- Teacher/admin test creation
- Manual subjective evaluation
- Structured error codes for diagnosis
- MySQL as the persistent source of truth
- Student result and performance-report views
- Cumulative question/performance history foundation

## Architecture

```text
Student Website
      ↓
 Flask / API
      ↓
 MySQL
      ↓
 Evaluation / Analytics / Diagnosis
      ↓
 Performance Report + Student Profile
      ↓
 Next Assessment
```

Planned orchestration and communication can use n8n, Python reporting/analytics, email, and WhatsApp. These integrations are not the core exam engine.

## Repository structure

```text
.
├── exam_platform/
│   ├── app.py
│   ├── admin.py
│   ├── db_source.py
│   ├── database.py
│   ├── evaluation.py
│   ├── diagnosis.py
│   ├── diagnostic_rules.py
│   ├── diagnostic_rules_adapter.py
│   ├── models.py
│   ├── question_selection.py
│   ├── reporting.py
│   ├── student_profile.py
│   ├── storage.py
│   ├── mock_data.py
│   ├── static/
│   └── templates/
├── database/
├── question_bank/
├── .env.example
├── .gitignore
├── PRODUCT_WORKFLOW.md
├── PRODUCT_STRATEGY.md
├── EXAM_PLATFORM_REPORT.md
├── PLATFORM_VERIFICATION.md
├── SESSION_SUMMARY.md
└── README.md
```

The current structure is intentionally kept stable before functional testing. Structural refactoring is a later phase.

## Data model direction

The system is designed to retain structured history at question level, including:

- Student ID and registration information
- Test ID and test metadata
- Question ID and question metadata
- Marks awarded
- Attempt/response status
- Evaluation error codes and comments
- Handwritten answer-image references
- Question history across tests
- Longitudinal performance data

This enables analysis of recurring errors rather than only reporting scores.

## Error taxonomy

The initial evaluation codes are:

- C01 — Calculation
- C02 — Conceptual
- C03 — Formula
- C04 — Sign
- C05 — Incomplete steps
- C06 — Wrong method
- C07 — Missing justification
- C08 — Misunderstood question
- C09 — Time/attempt

These codes may evolve as real student data is collected.

## Current development stage

The platform is at the **pre-functional-testing MVP stage**.

The next step is to run the application locally with MySQL and test the complete flow end to end. Until that test is completed, production readiness must not be assumed.

## Before public launch

Production hardening will still be required, including:

- Secure environment configuration and secrets
- Authentication and authorization hardening
- Server-authoritative timing
- Attempt locking and duplicate-submission protection
- Secure image/object storage
- File validation and size limits
- HTTPS
- Rate limiting
- Database backups
- Error logging and monitoring
- Evaluation audit trail
- Secure report access
- Privacy/consent handling

## Intentionally deferred

The MVP does not require AI grading, handwriting OCR, fully adaptive testing, parent/tutor dashboards, mobile apps, multiple subjects, State Boards, JEE, or a large subscription platform.

Those should be considered only after the assessment-and-diagnosis loop is validated with real paying students.
