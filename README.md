# Improvia — Mathematics Assessment & Improvement System

Improvia helps students understand **where they lose marks, why they lose them, what to practise next, and whether they improve**.

It is designed as a diagnostic assessment system, not simply a collection of mock tests.

**Core loop:** Register → Assess → Submit → Evaluate → Diagnose → Report → Recommend practice → Reassess → Measure improvement.

## Current pilot scope

### Mathematics
- Classes 9–12.
- CBSE and ICSE where the relevant curriculum and question bank have been validated.

### Computer-related subjects
- Class 10 CBSE Information Technology (Code 402).
- Class 10 CBSE Computer Applications (Code 165).
- Additional subjects or classes should be added only after curriculum validation.

Keep Information Technology (402) and Computer Applications (165) as distinct subjects. Do not represent them as one ambiguous “Computer” subject.

The intended pilot is controlled and founder-operated. Technical support for a subject does not by itself mean that subject is approved for launch.

## Product principles

A useful report should go beyond a score such as **62 / 80** and help answer:

- Where were marks lost?
- Why were they lost?
- Which mistakes appear repeatedly?
- Which chapters or skills need attention?
- What should the student practise next?
- Did performance change on the next assessment?

Handwritten Mathematics work is important to this workflow. Subjective answers should initially be marked by a human. AI grading is not part of the approved MVP; any future AI suggestions must remain human-reviewed and be validated against reference marking.

## Assessment workflow

1. **Registration and eligibility** — review registration information and grant access to the appropriate assessment.
2. **Assessment** — the student opens the website, answers questions, and works within the assessment's time and attempt rules.
3. **Submission** — preserve submitted answers and attempt state.
4. **Evaluation** — automatically score supported objective questions and have a teacher manually evaluate subjective work.
5. **Diagnosis** — record marks, relevant error categories, and clear comments.
6. **Report and history** — show results and useful performance history.
7. **Next practice** — recommend a focused next step and compare results after reassessment.

The complete workflow must be verified end to end before a public launch. A feature being present in code or documentation is not, by itself, proof that the whole workflow is production-ready.

## Mathematics error taxonomy

The initial Mathematics diagnostic categories are:

| Code | Category |
|---|---|
| C01 | Calculation |
| C02 | Conceptual |
| C03 | Formula |
| C04 | Sign |
| C05 | Incomplete steps |
| C06 | Wrong method |
| C07 | Missing justification |
| C08 | Misunderstood question |
| C09 | Time/attempt |

Use these codes consistently when supported by the marking evidence. An unanswered question alone does not prove a conceptual weakness. Other subjects need suitable subject-specific diagnosis rather than automatically inheriting the Mathematics taxonomy.

## Current application and architecture

The application uses Python, Flask, Jinja2, SQLAlchemy, and MySQL. The repository includes student exam routes, teacher/admin workflows, question-bank and curriculum components, evaluation and diagnosis code, and reporting functionality.

### Production and development databases

The documented production topology is:

```text
Production
Student browser
    ↓
Render / Flask application
    ↓
DATABASE_URL
    ↓
Aiven MySQL

Local development
Developer machine
    ↓
Local MySQL
    ↓
Local testing and development
```

- `DATABASE_URL` selects the application's configured database connection.
- `QUESTION_BANK_SYNC_DATABASE_URL` is an optional question-bank synchronization connection; it is not general-purpose student-data replication.
- Do not assume local MySQL and Aiven are continuously synchronized.
- Never run unapproved production migrations or destructive database operations.

See [PRODUCTION_ARCHITECTURE.md](PRODUCTION_ARCHITECTURE.md) for registration and environment details, and [PRODUCT_WORKFLOW.md](PRODUCT_WORKFLOW.md) for the fuller product workflow.

## Registration during the controlled launch

The documented founder-operated process is:

```text
Google Form
    ↓
Google Sheets
    ↓
Manual review and confirmation
    ↓
Create or reuse permanent Student_ID
    ↓
Production database
    ↓
Assessment access
```

Google Sheets can hold raw registration responses during the pilot. The production database remains the source of truth for enrolled students and assessment data. Review the registration and enrollment flow before using it with real students.

## Local development

Use Python 3.12 or another version supported by the project's configuration.

From the repository root, on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Configure local environment variables using the repository's `.env.example` and your local MySQL setup. Use local, synthetic test data; do not place production credentials in source control. Do not copy production secrets into logs, screenshots, tests, or documentation.

Run the focused tests relevant to a change, for example:

```powershell
python -m pytest -q tests/test_question_model.py
```

To run the full test suite, first inspect the test configuration and confirm the database settings are isolated from production. Some application/database modules perform schema initialization when imported; **do not run tests against production credentials or a production database**.

The exact commands needed to run the web application depend on local environment configuration. Verify configuration and database safety before starting it.

## Security, privacy, and data integrity

Students may be minors. Treat names, contact information, handwritten work, submissions, marks, reports, and performance history as private student data.

Before public launch, verify at minimum:

- Authentication and authorization for student and teacher actions.
- Per-student ownership checks for attempts, uploads, responses, reports, and results.
- Private answer-image storage and access-controlled retrieval.
- CSRF protection on state-changing routes.
- Server-side deadlines, attempt-state transitions, and duplicate-submission handling.
- Upload type and size validation.
- Production secrets and environment configuration.
- Database schema/migration history, backups, and restore procedures.
- Registration-to-report workflow and report figures against hand-checked examples.

This checklist identifies areas to verify; it does not claim every item is currently defective or that every item has been production-verified.

## Current development stage

Improvia is in controlled functional testing and pre-public-launch preparation. The immediate priority is to establish a reliable assessment-to-report loop and validate the quality and usefulness of feedback with a small supervised cohort.

Recommended sequence:

1. Reconcile and verify security and release-readiness work.
2. Prove registration, eligibility, assessment, answer persistence, submission, evaluation, diagnosis, report delivery, and performance history end to end.
3. Hand-check reports and record marking workload and student/guardian feedback.
4. Run a small supervised pilot before expanding the cohort.
5. Add automation or more subjects only when evidence supports it.

## Intentionally deferred

Unsupervised AI grading, handwriting OCR, fully adaptive testing, parent/tutor dashboards, mobile apps, and large-scale subscription features are not prerequisites for the initial MVP. Prioritize reliable evaluation, actionable diagnosis, privacy, and measured student improvement over adding technology for its own sake.

## Repository guidance

- Read [docs/CHATGPT_INSTRUCTIONS.md](docs/CHATGPT_INSTRUCTIONS.md) before making repository changes.
- Keep changes small, focused, and testable.
- Inspect existing code, tests, migrations, and branch/PR dependencies before implementation.
- Do not commit secrets, real student data, local database dumps, or temporary artifacts.
- Report the exact tests run and their results; targeted test success is not proof of production readiness.
