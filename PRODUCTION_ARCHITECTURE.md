# Improvia Production Architecture and Release Boundaries

## Purpose and release status

This document describes the intended architecture after the V1 hardening changes in PR #31. It is **not proof that the live Render/Aiven environment has been migrated or verified**. The live deployment commit, environment variables, schema, Cloudinary behavior, and auto-deploy setting must be checked in the provider dashboards before release.

## Intended production topology

```text
Student browser
   |
   v
Render / Flask application
   |-- student login, assessment, submission, results, report
   |-- authenticated teacher/operator endpoints
   |-- private answer-image proxy
   |
   +--> DATABASE_URL --> Aiven MySQL
   |       students and enrollments
   |       tests, questions, attempts, responses
   |       evaluation errors and performance history
   |       student credentials and one-time activation tokens
   |
   +--> CLOUDINARY_URL --> private hosted answer-image storage
```

Aiven is the intended production source of truth for student and assessment records. The optional `QUESTION_BANK_SYNC_DATABASE_URL` mechanism is only for question-bank synchronization; it is not student-data replication.

## Student registration and access lifecycle

1. A registration is received and reviewed through the current registration workflow.
2. The registration pipeline validates the approved student's board, class, subject, and academic-year curriculum.
3. The pipeline creates or reuses a permanent Student ID and persists the active enrollment idempotently.
4. An authenticated teacher/operator issues a time-limited activation link for that enrolled student.
5. The student activates the account with a password of at least 12 characters. The activation token is single-use and only its hash is stored.
6. The student logs in to access their own assessments, submissions, results, reports, and answer images.
7. Failed login attempts are temporarily locked after repeated failures. Logout clears the session.
8. Anonymous/guest access must not create a permanent student identity or expose assessment records.

The access-link endpoint returns a sensitive activation URL. Deliver it privately to the intended student; do not post it in public channels, tickets, or logs. Do not ask students to send passwords over WhatsApp.

## Assessment and evaluation lifecycle

```text
Enrolled student
   -> authenticated assessment access
   -> save answers / upload required handwritten work
   -> submit attempt (submission becomes immutable)
   -> teacher reviews every response
   -> marks + structured error codes + comments
   -> readiness/completeness validation
   -> result and two-page PDF report
   -> next assessment updates longitudinal error history
```

The report must not be presented as final while evaluation is incomplete or inconsistent with the test's official maximum marks. The report should explain score, attempt rate, accuracy, chapter evidence, error patterns, strengths/weaknesses, and changes from an earlier assessment in student-friendly language.

## Data ownership and storage

| Data | Source of truth |
|---|---|
| Raw registration and customer-validation responses | Current registration workflow / Google Sheets, where used |
| Production student identity and enrollment | Aiven MySQL |
| Tests, questions, attempts, responses, marks, errors, history | Aiven MySQL |
| Uploaded handwritten answer images | Private hosted storage; access through authenticated application routes |
| Local development and CI test data | Isolated local/CI databases only |

Do not create a second continuously synchronized student database. Do not use production data as a test fixture.

## Deployment and schema safety

- Hosted startup must fail clearly when required production configuration or schema is missing. It must not silently fall back to local database defaults.
- Production startup validates schema read-only; schema creation and data backfills belong in explicit reviewed migrations.
- Migration 005 (curriculum/enrollment mapping) must be audited against the actual Aiven database before applying it.
- Migration 006 (student credentials and activation tokens) must be audited and then applied only after an approved, restorable backup.
- CI migration success proves behavior only against the disposable CI database; it does not prove production schema compatibility.
- Confirm the current Render deployment SHA, current environment variables, persistent storage configuration, Cloudinary credentials/access behavior, and whether auto-deploy is enabled.
- Do not merge a release candidate if merging may deploy it before the production migration and release checks are ready.
- Any production migration or live deployment requires the owner's explicit approval after the audit and rollback plan are presented.

## Backup and rollback

Before any production schema/data change:

1. Record the currently deployed commit and the current schema state.
2. Create an Aiven backup/snapshot and verify the provider-supported restore procedure.
3. Run the read-only migration audits and save sanitized output.
4. Review every expected schema/data change, including enrollment backfill counts and unmatched question mappings.
5. Obtain explicit approval before applying a migration.
6. Verify tables, required columns, representative read/write paths, and application health after the change.
7. Keep the previous application version available for rollback. Do not automatically drop new access tables during rollback because they may contain real account data.

Stop the release if schema assumptions, row counts, image delivery, or report generation differ from expectations. Never improvise destructive SQL against live student records.

## Current verification checklist

The repository's isolated CI workflow covers the end-to-end exam workflow and regression suite. The following are separate production gates and remain unverified until checked against the actual provider environment:

- [ ] Confirm deployed commit and Render auto-deploy behavior.
- [ ] Confirm required production environment variables without exposing their values.
- [ ] Run migration 005 read-only audit against Aiven.
- [ ] Run migration 006 read-only audit against Aiven.
- [ ] Verify backup and restore procedure.
- [ ] Review audit output and approve any migration.
- [ ] Apply approved migrations and verify schema.
- [ ] Deploy only after the migration and release gates pass.
- [ ] Verify registration/access, test submission, private image access, teacher evaluation, report/PDF, and second-assessment history on the deployed site.
- [ ] Record deployed SHA and sanitized acceptance evidence.

Mark any check that cannot be run against the real environment as **unverified**, not passed.
