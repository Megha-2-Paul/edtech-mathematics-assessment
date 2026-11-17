# Platform Verification and Release Readiness

**Last documentation review:** 17 November 2026  
**Scope:** repository code and recorded CI evidence; no live production verification  
**Current stage:** local-first development, controlled functional testing and pre-public-launch preparation

## 1. How to read this document

This document separates four different kinds of evidence:

- **Implemented in repository:** code or tests exist in the inspected source. This does not prove the workflow works end to end.
- **CI-verified:** a specific commit has a successful CI result. This proves only the checks included in that workflow and commit.
- **Requires local verification:** the owner still needs to run and manually verify the workflow on the intended local environment.
- **Not production-verified:** no live production configuration, student workflow, backup/restore, privacy or operational control was independently verified by this documentation review.

A feature should not be labelled production-ready solely because a route, test, migration, document or merged PR exists.

## 2. Implemented foundations observed in the repository

The current repository includes:

- Flask application and student assessment routes.
- Student login, logout and activation route foundations.
- Student access enforcement and CSRF protection code.
- Teacher access-link and teacher workflow foundations.
- Google Form registration webhook endpoint.
- Assessment listing, instructions, attempt creation and question retrieval.
- Response saving, answer-image upload/retrieval/deletion and submission preview/confirmation routes.
- Manual teacher evaluation, marks validation and structured error-code persistence.
- Diagnosis, deterministic report generation and student performance-history foundations.
- Question-bank ingestion/provenance and curriculum mapping foundations.
- MySQL-backed storage and migration/bootstrap code.
- Migration manifest, ledger helpers, legacy migration adoption checks and CI migration tests.

These are implementation observations, not a statement that every route and workflow has been manually exercised on the owner's laptop.

## 3. PR and CI evidence

### PR #35 — student access and private upload work

PR #35 was merged into master on 17 November 2026. The recorded GitHub Actions run associated with the post-merge master commit completed successfully:

- Merge commit: `acbf06f6fe9844a25331fe5b10185a1196db226b`
- Workflow run: [GitHub Actions run 44080558045](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/actions/runs/44080558045)

The previously reported PR test result was 363 passed with 5 warnings. Treat that as the result reported for that PR run, not as a fresh local run or proof of production readiness. Re-check the run and current CI configuration if exact job-level evidence is needed.

### PR #38 — migration ledger and adoption checks

PR #38 is included in the inspected master history. It adds migration-ledger execution metadata, a migration manifest, read-only legacy migration adoption checks, and MySQL-backed CI coverage. The existence of these tests is not proof that any local or production database has been upgraded or adopted.

No migration was executed as part of this documentation update.

## 4. Local end-to-end verification backlog

Run these checks using synthetic data and an isolated local database:

1. Confirm the application starts against the intended local database.
2. Verify registration webhook validation, duplicate handling and student identity behaviour.
3. Verify student activation, login, logout, session handling and invalid/expired token behaviour.
4. Verify student ownership checks across attempts, responses, reports and answer images.
5. Verify assessment listing, eligibility, instructions and attempt creation.
6. Verify answer persistence across navigation, refresh and reconnect.
7. Verify upload type/size validation, multiple image behaviour, deletion and private retrieval.
8. Verify server-side timing, expiry, resume and attempt-state transitions.
9. Verify submission preview, required uploads, unanswered questions and duplicate/concurrent submissions.
10. Verify teacher authentication/authorisation and access-link workflow.
11. Verify manual marking, partial marks, multiple error codes and re-evaluation.
12. Verify diagnosis calculations against hand-calculated examples.
13. Verify report totals, accuracy definitions, chapter/topic summaries and recommendation logic.
14. Verify report ownership and access isolation.
15. Verify longitudinal history and reassessment comparisons.
16. Verify failure recovery for database errors, upload failures and interrupted requests.
17. Verify phone-sized layouts and keyboard/accessibility basics.
18. Record measured response time and memory use with representative synthetic data.

Record each check as pass, fail, blocked or not run, with date, environment, commit and evidence. Do not convert a planned check into a completed one.

## 5. Migration and database safety

- Do not connect this documentation task to local or production databases.
- Do not run schema bootstrap, migration, adoption, ledger recording or seed operations as a documentation check.
- The migration adoption verifier is read-only and may report `UNKNOWN` where schema inspection cannot prove data effects.
- The ledger upgrade script requires an explicit `--dry-run` or `--apply` mode and a database URL. `--apply` changes schema.
- The migration manifest currently lists migration IDs 001–006 and 008. Migration 007 is not listed in that manifest at the inspected commit; do not infer that it is safe to execute or automatically adopt.
- A successful CI MySQL service run uses its own CI database; it does not certify the state of a developer's local database or Aiven.

Any local database verification must first confirm the effective target is an isolated local/test database. Production database actions require a separate explicit owner decision, backup and review.

## 6. Production-readiness gates

Before real student use, verify and document:

- Authentication, authorisation and cross-student isolation.
- Teacher/admin privilege boundaries and secure credentials.
- CSRF coverage and secure session/cookie configuration.
- Server-authoritative timing and immutable/controlled submission state.
- Private and durable handwritten-answer storage.
- Upload validation and resource limits.
- Correctness of marks, diagnosis, reports and progress history.
- Privacy notice, consent, retention and deletion handling for minors' data.
- Backup, restore, monitoring, incident response and operational ownership.
- Capacity and performance under representative concurrent use.
- End-to-end registration-to-report workflow with a small supervised pilot.

## 7. Current delivery strategy

Development and testing remain **local-first**. Finish the application workflows, validate them on the laptop and measure performance before selecting a hosting provider or production database arrangement. Hosting cost, scalability, latency, operational burden and database compatibility will be evaluated later.

No deployment, hosting migration or production database change is authorised by this verification document.

## 8. Related references

- [README.md](../../README.md)
- [QUICK_START.md](../operations/QUICK_START.md)
- [PRODUCT_WORKFLOW.md](../product/PRODUCT_WORKFLOW.md)
- [PRODUCTION_ARCHITECTURE.md](../architecture/PRODUCTION_ARCHITECTURE.md)
- [Database schema and architecture](../architecture/DATABASE_SCHEMA_AND_ARCHITECTURE.md)
- [Migration inventory](../database/MIGRATION_INVENTORY.md)
- [Consolidated development audit](DEVELOPMENT_AUDIT.md)
