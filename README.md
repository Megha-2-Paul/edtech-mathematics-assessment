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

## Supporting research tool — NotebookLM

[NotebookLM](https://notebooklm.google.com/) is included in the project workflow as a **supporting research and knowledge tool**, not as part of the core assessment engine.

It can be used to work with authoritative/permitted source material such as CBSE/ICSE documents, sample papers, marking schemes, licensed content and the business's own material. Intended uses include:

- syllabus and curriculum research
- marking-scheme research
- question-bank research and classification
- assessment/content validation
- source-grounded educational research
- internal founder research

NotebookLM should **not** own student records, exam timing, submissions, grading, error coding, analytics, diagnosis, recommendations, report generation, authentication or payments.

The production source of truth remains the application database and structured business logic. Final mathematical and assessment decisions must be human-validated.

See [`NOTEBOOKLM_WORKFLOW.md`](NOTEBOOKLM_WORKFLOW.md) for the operating procedure, boundaries, suggested notebooks and roadmap placement.

## Automation strategy

The MVP should automate repetitive operational work while keeping mathematical judgment human-controlled.

The preferred operating model is:

> **The founder evaluates the student's mathematics once; the system performs the repetitive work around that evaluation.**

### Automate early

- Student IDs and database records
- Objective scoring
- Score, percentage and attempt calculations
- Chapter/topic/error analysis
- Longitudinal comparison and recurring-error detection
- Student-profile updates
- Charts and individual PDF reports
- Scheduled reminders and report delivery

### Keep human-controlled initially

- Subjective mathematics evaluation
- Ambiguous answer decisions
- Final marks
- Uncertain error classification
- Question-quality decisions
- Customer support and feedback interpretation

### Tool roles

- **Flask + MySQL:** core student/exam system and source of truth
- **Python/pandas:** scoring, analytics, diagnosis and recommendations
- **ReportLab:** report generation
- **n8n:** workflow orchestration and integrations, not core mathematical logic
- **Email:** formal report/record delivery
- **WhatsApp Business API:** high-engagement notifications as the communication layer matures
- **NotebookLM:** internal source-grounded research and question/content support

See [`AUTOMATION_WORKFLOW.md`](AUTOMATION_WORKFLOW.md) for the detailed automation matrix, boundaries, priorities and V1–V5 evolution.

## Architecture

```text
                  SOURCE / KNOWLEDGE LAYER

 CBSE/ICSE official or permitted sources + own material
                          ↓
                     NotebookLM
               Research / source analysis
                          ↓
                  Validated decisions
                          ↓
                    Question Bank
                          ↓
 Student Website → Flask/API → MySQL
                          ↓
                  Human Evaluation
                          ↓
              Python Analytics / Diagnosis
                          ↓
              Report + Student Profile
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
├── AUTOMATION_WORKFLOW.md
├── PRODUCT_STRATEGY.md
├── NOTEBOOKLM_WORKFLOW.md
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
