# Local Development Quick Start

> **Status:** Safe setup guidance for the current repository. This document replaces older prototype instructions that used a developer-specific Windows path, hard-coded demo questions, and test output that should not be treated as current verification evidence.

## 1. Before starting

- Work from your own clone of `edtech-mathematics-assessment`.
- Use the repository's current `master` or the task branch you intend to test.
- Use Python 3.12 (the project has been developed with Python 3.12).
- Install and start a local MySQL 8 instance for development.
- Use synthetic test data only.
- Do not use production/Aiven credentials or a production database for local testing.

The application and database modules can initialise schema or load data during import/startup. Confirm the database target before running the application or tests.

## 2. Create the Python environment

From PowerShell, in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, you can call the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe --version
```

Do not install additional analysis tools or dependencies without reviewing their compatibility and getting approval where required.

## 3. Configure a local database

1. Review `.env.example` to understand the supported variable names.
2. Create a local-only `.env` file; never commit it.
3. Configure the database to point to your local MySQL instance and a dedicated development database.
4. Confirm the selected database name and host without printing passwords, tokens, or the full connection URL.
5. Keep production credentials and Aiven URLs out of the local environment.

The optional `DATABASE_URL` takes precedence where configured; otherwise the application can use the individual `DB_*` settings. Verify the effective target without exposing credential values before importing application modules or running tests.

**Do not run migrations as part of quick-start setup.** Migration audit, dry-run and apply operations are separate, explicitly reviewed tasks. In particular, never run migration scripts against Aiven or another production database.

## 4. Run tests safely

Before running any test:

- Inspect `pytest.ini`, `conftest.py`, test fixtures and relevant imports.
- Determine whether the test creates tables, seeds data, or connects to MySQL.
- Confirm the effective database is a disposable or isolated local test database.
- Check whether importing the application triggers schema initialisation.
- Run the smallest relevant test first.

Example command (only after confirming isolation):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests
```

This is a command template, not a claim that the current full suite has been executed or passed. Report the exact command and actual result. Do not copy old expected-output blocks as evidence.

## 5. Start the application

There is no unconditional startup command in this quick-start guide because application startup can initialise the database and load configured data. First inspect the current entry point and environment configuration, confirm the target is local, and then use the repository's current supported entry point.

Do not assume an old command, demo dataset, port, or sample test remains valid.

## 6. Local workflow verification

Verify the actual current implementation in controlled stages:

1. Application starts against the intended local database.
2. Student registration and eligibility behave as expected.
3. Student authentication/activation and access controls behave as expected.
4. Assessment listing, instructions and attempt creation work.
5. Answers persist across navigation and refresh.
6. Image upload, retrieval and deletion respect access controls.
7. Timing and expiry are enforced server-side.
8. Submission is complete and duplicate submission is handled safely.
9. Teacher access and manual evaluation work.
10. Diagnosis, report values and student history reconcile with hand-calculated examples.

Use synthetic accounts and records. Do not use real student information during development verification.

## 7. Troubleshooting

- **Database connection error:** verify local MySQL is running, the development database exists, and the effective host/database target is local.
- **Unexpected schema error:** stop; do not try random migrations or destructive repairs. Capture the non-secret error and inspect the migration/bootstrap state.
- **Tests unexpectedly touch a database:** stop the run and inspect fixtures/configuration before retrying.
- **Application starts with unexpected data:** check demo-data settings and the target database; do not delete records until the database is positively identified as disposable.
- **Port conflict:** inspect the process using the configured port before stopping anything.

## 8. Related documentation

- [README.md](../../README.md) — product scope and repository overview.
- [PLATFORM_VERIFICATION.md](../engineering/PLATFORM_VERIFICATION.md) — implementation, CI evidence and local verification backlog.
- [PRODUCT_WORKFLOW.md](../product/PRODUCT_WORKFLOW.md) — canonical product workflow and roadmap distinction.
- [PRODUCTION_ARCHITECTURE.md](../architecture/PRODUCTION_ARCHITECTURE.md) — historical production topology and registration architecture.
- [docs/architecture/DATABASE_SCHEMA_AND_ARCHITECTURE.md](../architecture/DATABASE_SCHEMA_AND_ARCHITECTURE.md) — schema reference and design proposals.
- [docs/architecture/MIGRATION_INVENTORY.md](../database/MIGRATION_INVENTORY.md) — migration inventory and safe execution boundaries.
- [docs/IMPROVIA_DEVELOPMENT_AUDIT.md](../engineering/DEVELOPMENT_AUDIT.md) — audit scope, evidence and outstanding risks.

## Current development policy

Build and verify locally first. Decide on hosting and production database architecture only after the end-to-end product workflow and representative performance have been tested. No deployment or production database action is authorised by this document.
