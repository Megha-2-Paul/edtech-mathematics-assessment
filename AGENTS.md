# AGENTS.md — Improvia Development Instructions

## 1. Project Overview

Improvia is a mathematics assessment and learning platform for CBSE and ICSE students.

Its core workflow includes:
- Student registration and eligibility.
- Assessment creation and question selection.
- Student assessment attempts and submissions.
- Evaluation and error diagnosis.
- Personalised feedback and recommended practice.
- Reports and longitudinal progress tracking.

Preserve the existing product behaviour and business rules unless a change is explicitly approved.

## 2. Instruction Priority

Before making changes, read:

- `README.md`
- `docs/CHATGPT_INSTRUCTIONS.md`
- Relevant architecture, workflow, migration and testing documentation.

This file supplements the repository's existing instructions. Where operational details differ, follow the more specific requirements in `docs/CHATGPT_INSTRUCTIONS.md`.

## 3. Technology and Architecture

The project uses Python, Flask, Jinja2, SQLAlchemy and MySQL, alongside its existing supporting libraries and services.

Important environment distinctions:
- Local development uses a local database.
- Production uses Aiven MySQL.
- Never assume local and production databases are synchronised.
- `DATABASE_URL` is the application database connection.
- `QUESTION_BANK_SYNC_DATABASE_URL` is for the specific question-bank synchronisation workflow, not general student-data replication.

Inspect the existing architecture before proposing changes. Do not introduce a new framework or architectural pattern without a clear, approved reason.

## 4. Mandatory Development Workflow

For every task:

1. Understand the requested outcome and inspect the relevant existing implementation.
2. Read the applicable project instructions and documentation.
3. Inspect the current Git state and relevant branches or pull requests.
4. Prepare a written plan before modifying files.
5. Include current behaviour, proposed behaviour, files affected, files excluded, database implications, tests, risks and regression possibilities.
6. Wait for explicit approval of the plan.
7. Implement only the approved scope.
8. Run appropriate tests and inspect the final diff.
9. Provide a clear handoff with exact commands and results.

If the investigation reveals a requirement outside the approved scope, stop and ask before proceeding.

## 5. Code Quality and AI-Generated Code

Actively inspect for:
- Duplicate or contradictory logic.
- Dead code and unused imports.
- Unnecessary abstractions and excessive helper functions.
- Overly complicated conditionals.
- Large functions with unrelated responsibilities.
- Broad exception handling that hides errors.
- Hardcoded configuration and magic values.
- Inconsistent validation and error handling.
- Unnecessary dependencies.
- Unclear naming and misleading comments.
- Code that appears complete but is not connected to the actual application workflow.

Do not refactor merely to make code look cleaner.

Preserve existing behaviour, interfaces, database contracts and user-facing workflows unless the approved task explicitly changes them.

## 6. Recommended Quality and Security Tools

Evaluate tools against the existing project environment before introducing them.

Potential tools include:
- Ruff — linting and basic code-quality checks.
- Vulture — detection of potentially unused code.
- Radon and Xenon — complexity measurement.
- Bandit — Python security checks.
- Semgrep — configurable static analysis.
- pip-audit — dependency vulnerability checks.
- deptry — dependency hygiene.
- pytest — automated testing.
- pytest-cov — test coverage.
- Mypy — optional static type checking.

Do not install every tool automatically. Recommend a minimal, useful toolset and explain its value, compatibility, maintenance cost and limitations before adding dependencies or CI steps.

Static-analysis findings must be reviewed; automated warnings are not automatically confirmed defects.

## 7. Database and Migration Safety

- Never execute production Aiven migrations or destructive database operations.
- Do not assume that a local database accurately represents production.
- Use an isolated local or disposable test database for database tests.
- Inspect existing schema and migration history before proposing changes.
- New migrations must be explicit, reviewable and safe to rerun where applicable.
- Preserve existing student, question, assessment and attempt identifiers.
- Document migration order, prerequisites, audit steps and rollback considerations.
- Prefer read-only audits before any schema-changing operation.
- Do not run schema initialisation or seed operations against production as part of testing.

The owner must review and execute any approved production migration separately.

## 8. Student Privacy and Application Security

Student information is sensitive. Students may be minors.

- Never expose real student records, credentials, tokens or private files in logs, test output, commits or external services.
- Never commit `.env` files, secrets, database URLs, API keys or credentials.
- Use environment variables or the existing secure configuration mechanism.
- Enforce authentication and authorisation on protected routes.
- Verify student ownership before exposing attempts, reports or uploaded answer images.
- Preserve CSRF protection for state-changing requests.
- Validate and constrain uploaded files and filesystem paths.
- Avoid leaking internal errors or sensitive data in responses.
- Do not send student information, handwritten answer images or other private records to third-party AI services without explicit approval.

## 9. Question Bank and Curriculum Integrity

Preserve the existing question-bank and curriculum contracts.

Important distinctions:
- CBSE and ICSE curriculum mappings must remain correct.
- CBSE Information Technology Code 402 and Computer Applications Code 165 are separate subjects.
- Curriculum taxonomy must not be silently changed or bypassed.
- Question provenance and source information must be retained.
- AI-generated question candidates must remain subject to the existing human-review process.
- Never publish unverified AI-generated questions automatically.

Do not change taxonomy identifiers, question identifiers or curriculum relationships without an approved migration and compatibility plan.

## 10. Assessment and Evaluation Integrity

Assessment correctness takes priority over cosmetic improvements.

Preserve:
- Server-side enforcement of assessment timing.
- Submission and attempt integrity.
- Protection against duplicate or repeated submissions.
- Student ownership and access checks.
- Consistent question and response relationships.
- Reliable calculation of marks and assessment metrics.
- Correct report generation and progress history.

Subjective mathematics marking must remain human-supervised unless a separate, explicitly approved feature changes this policy.

Do not introduce unsupervised AI grading.

## 11. Testing Requirements

Every behaviour-changing modification must have appropriate regression tests.

Prioritise tests for:
- Authentication and authorisation.
- Student ownership and cross-student isolation.
- Registration and eligibility.
- Assessment creation and attempt lifecycle.
- Timers and submission handling.
- Evaluation and report calculations.
- File upload validation and private file access.
- Question-bank and curriculum integrity.
- Database migration behaviour.
- Error handling and invalid input.

Do not delete, weaken, skip or rewrite valid tests simply to obtain a passing result.

Before running a full test suite:
- Inspect test configuration.
- Identify database connections and environment variables.
- Confirm that the test database is isolated from production.
- Check whether imports trigger schema initialisation or data changes.

Report exact commands, pass/fail counts, skipped tests and any tests not run. Never claim that a test passed unless it was actually executed.

## 12. Performance and Maintainability

Look for measurable opportunities to improve:
- N+1 database queries.
- Unnecessary repeated database access.
- Missing indexes on frequently queried fields.
- Loading all records when pagination is appropriate.
- Repeated expensive calculations.
- Unnecessary image or file loading.
- Unbounded data processing.
- Excessive coupling between unrelated modules.

Do not introduce caching, asynchronous processing or additional architectural layers without identifying a real problem and evaluating the trade-offs.

## 13. Product Scope Discipline

Do not start unrelated roadmap features while working on an approved task.

Examples of separate work include:
- Tuition-centre website development.
- New question-ingestion providers.
- Groq-based PDF extraction.
- Shaalaa parsing or additional URL ingestion.
- Cloud-to-local database synchronisation.
- Credits, referrals or payment features.

Do not treat a planned feature as approval to implement it.

## 14. Documentation

Documentation must reflect actual application behaviour.

When changing a workflow, update the relevant documentation only within the approved scope.

Avoid duplicating detailed instructions unnecessarily. Link to the existing authoritative documentation where appropriate.

## 15. Final Engineering Principle

Stabilise before expanding.

Prefer small, measurable, testable changes that protect existing functionality and student data.

Reliability, data integrity, security and maintainability are more important than cosmetic refactoring or adding tools for their own sake.
