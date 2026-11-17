# Database Migration Inventory

> **Status:** Package 1A audit artifact; no migration runner or database operation is introduced.
> **Reviewed branch:** `fix/student-auth-private-uploads`
> **Reviewed commit before this inventory:** `8f8dc187a47f0dc71c61ace1a687210a9b152469`

## Purpose

This inventory records what each schema script does, what it depends on, which application features consume its schema, and how it must be executed. It is a code-level inventory, not evidence that a migration has run in any database.

The inventory deliberately separates:

- application bootstrap schema in `database.py`;
- schema-changing migrations;
- read-only audit/helper scripts;
- runtime dependencies;
- legacy or superseded schema.

No database URL, credentials, or live database state is included.

## 1. Execution inventory

| Script | Type / execution mechanism | Schema effects | Data effects | Tracking / idempotency notes |
|---|---|---|---|---|
| `database.py:SCHEMA` and `initialize_database()` | SQLAlchemy bootstrap for local/test; production (`RENDER=true`) validates only | Creates 29 tables with `CREATE TABLE IF NOT EXISTS`; performs compatibility ALTERs | Seeds legacy subjects, chapters and competencies; normalizes empty student email | No unified migration-ledger record. Bootstrap is not a substitute for migrations 001 or 007, nor for taxonomy data seeding in 005. |
| `001_question_bank_foundation.sql` | MySQL-client script; contains `DELIMITER`, a stored procedure, CALL and DROP PROCEDURE | Creates `schema_migrations` plus 10 source/extraction tables; adds question provenance fields/indexes and question asset metadata/index | Normalizes question source/verification values | Checks/inserts `001_question_bank_foundation` in `schema_migrations`. Not safe to split naively into ordinary SQLAlchemy statements. |
| `002_canonical_question_ingestion.sql` | MySQL-client script; contains `DELIMITER` and a stored procedure | Ensures provenance columns; creates `question_solutions` | Backfills `canonical_question_id` from `question_id` when absent | Checks/inserts `002_canonical_question_ingestion` in `schema_migrations`. Several columns and `question_solutions` overlap the current bootstrap definition. |
| `003_canonical_math_taxonomy.py` | Python / SQLAlchemy metadata creation | Creates legacy `canonical_subjects`, `canonical_chapters`, `syllabus_units`, `syllabus_chapters` | Inserts taxonomy subjects, chapters, units and mappings | Additive; no shared migration-ledger integration identified. Its taxonomy is explicitly marked legacy/superseded by the newer model. Do not apply or remove without consumer verification. |
| `004_student_registration_subject.sql` | MySQL-client script using INFORMATION_SCHEMA, PREPARE and EXECUTE | Adds `students.subject` if absent and creates `idx_students_eligibility` if absent | No intentional row backfill | Idempotent existence checks; no shared migration-ledger record. The subject column is still used as a compatibility input by current registration code. |
| `005_curriculum_question_reuse.py` | Python / SQLAlchemy | Creates the seven current subject/curriculum/enrolment tables | Seeds subject/curriculum/concept/chapter taxonomy; backfills active Mathematics/Applied Mathematics enrolments for academic year 2026-27; inserts exact question-to-curriculum matches | Uses upserts/INSERT IGNORE for repeatability, but has no shared migration-ledger record. It is a schema **and data** migration. |
| `005_curriculum_question_reuse_audit.py` | Python / SQLAlchemy read-only audit | No schema changes | Reads counts and predicts enrolment/question mapping backfills | Read-only helper used by migration 005 dry-run. Not an apply migration. |
| `006_exam_monitoring_mode.py` | Python / SQLAlchemy | Adds or repairs `tests.monitoring_mode` | Normalizes null/invalid values to `off` | Has dry-run/apply modes; no shared migration-ledger record. Column already exists in current bootstrap, so this is principally a legacy repair path. |
| `007_student_access.py` | Python / SQLAlchemy | Creates `student_access_credentials` and `student_access_tokens` with FK/index constraints | No student credential rows are seeded | Default is read-only audit; `--apply` required. Verifies schema after creation; no shared migration-ledger record. |
| `008_migration_ledger_upgrade.py` | Python / SQLAlchemy; explicit `--dry-run` or `--apply` | Creates `schema_migrations` if absent and adds six execution-metadata columns after validating the legacy ledger contract | No migration data backfill | Additive and rerunnable; preserves `migration_id`/`applied_at`; dry-run makes no database changes; does not record its own completion. |
### Supporting code facts

- `database.py` defines 29 bootstrap tables.
- Migration 001 defines 11 tables including the migration ledger itself.
- Migration 007 defines 2 student-access tables.
- Migration 002 overlaps bootstrap definitions for provenance fields and `question_solutions`.
- Migration 005 overlaps bootstrap table definitions for all seven current curriculum tables, but additionally performs required taxonomy seeding and backfills.
- Migration 004 overlaps the bootstrap addition of `students.subject`; its eligibility index is not present in the shown bootstrap DDL.
- Migration 006 overlaps the bootstrap definition of `tests.monitoring_mode`.

These are definitions in repository code, not a verified live-database table count.

## 2. Runtime dependency classification

| Schema group | Runtime consumers found | Classification |
|---|---|---|
| Core student, question, test, attempt, response, image tables | `exam_platform/storage.py`, `exam_platform/db_source.py` and related exam flows | **Core runtime required** |
| `subject_catalog`, `student_subject_enrollments` | `exam_platform/eligibility.py` reads both; `exam_platform/storage.py` writes enrolments | **Core runtime required** for current registration/eligibility behaviour |
| `curriculum_catalog`, `curriculum_units`, `canonical_concepts`, `curriculum_chapters`, `question_curriculum_map` | Current curriculum/question-reuse implementation and migration audit; confirm every production query before narrowing requiredness | **Feature/runtime dependency**; preserve |
| `student_access_credentials`, `student_access_tokens` | Student authentication and activation flows | **Core runtime required** when student access is enabled |
| `question_solutions`, `question_assets`, extraction review tables | Question solution/media and extraction-review paths | **Feature-specific required** when those workflows are enabled |
| Migration 001 provenance/extraction tables | Extraction design and review documentation; the currently inspected review UI also uses local JSON review state and existing storage methods | **Feature-specific / adoption incomplete**; do not assume all tables are already used by every live path |
| Legacy `subjects`, `chapters`, `competencies` | Bootstrap seed and legacy lookup/fallback code | **Compatibility schema** until all consumers are verified as migrated |
| Legacy taxonomy tables from migration 003 | Legacy taxonomy artifact; current review UI resolves the older JSON taxonomy, while current eligibility uses the newer enrollment model | **Legacy / superseded**; no automatic removal or application |

### Directly confirmed runtime dependencies

1. `exam_platform/eligibility.py` queries `student_subject_enrollments` joined to `subject_catalog` for both test eligibility and registration completeness.
2. `exam_platform/storage.py` inserts/updates subject enrolments. Its mapping currently derives from one legacy `Student.subject` and uses a fixed academic year.
3. `exam_platform/storage.py` loads the core operational tables and reads/writes question, test, student and attempt records.
4. `question_bank/extraction/review_app.py` uses `CanonicalTaxonomyResolver` and question storage/asset methods. Its current review queue and review status are file-backed JSON; that is not proof that the migration 001 review tables are wired into this UI.
5. `exam_platform/db_source.py` delegates compatibility writes to legacy storage while serving core reads from MySQL.

The above classification is conservative. A table is not declared optional merely because a text search did not find a reference.

## 3. Migration dependency and ordering

The current scripts imply the following dependency constraints:

1. A compatible `students`, `questions` and `question_assets` base schema must exist before migration 001.
2. Migration 002 requires `questions`; it creates/uses `schema_migrations` and adds `question_solutions`. Its overlap with `database.py` must be reconciled before choosing a fresh-install path.
3. Migration 003 requires an existing database connection and the taxonomy JSON; it is a legacy taxonomy branch, not a prerequisite for current curriculum eligibility.
4. Migration 004 requires `students`.
5. Migration 005 requires the core `students` and `questions` tables and the expected legacy columns. It creates the new curriculum tables and then seeds/backfills them. Its audit script is read-only.
6. Migration 006 requires `tests`.
7. Migration 007 requires `students.student_id VARCHAR(32)` compatible with the child foreign keys.

This is a dependency summary, **not yet an approved execution order**. A unified fresh-install plan must resolve duplicate DDL, seed requirements, MySQL-client-only syntax and migration tracking before any database changes.

## 4. Migration-ledger gap

Only migrations 001 and 002 currently use `schema_migrations` to record their own completion. Migrations 003, 004, 005, 006, 007 and 008 do not consistently register themselves there. Migration 008 extends the ledger schema but does not record its own completion.

A ledger entry alone would not prove that a migration is safe or complete. In particular:

- migration 005 has both schema and data effects;
- migration 006 can normalize existing values and alter a column definition;
- migration 007 performs a post-apply schema audit;
- migrations 001 and 002 use MySQL stored-procedure syntax that needs a compatible execution mechanism.

**Package 1A does not add ledger writes or change migration behaviour.** A later package must design a versioned ledger contract, checksums, transactional/DDL limitations, failure recovery and adoption of already-applied legacy migrations.

## 5. Risks and decisions reserved for later packages

| ID | Risk / question | Current disposition |
|---|---|---|
| INV-01 | Bootstrap and migrations create overlapping schema objects with potentially different definitions | Reconcile exact columns, indexes, constraints and defaults before changing bootstrap |
| INV-02 | Migration 001 requires MySQL-client delimiter/procedure handling | Preserve compatible execution; do not pass whole file blindly to SQLAlchemy |
| INV-03 | Migration 005 performs taxonomy seeding and backfills in addition to DDL | Preserve and test data effects separately from table creation |
| INV-04 | Migration 003 represents a superseded taxonomy model | Retain until all consumers and historical deployments are understood |
| INV-05 | Migrations 003–008 are not consistently recorded in the shared ledger | Design safe adoption/ledger strategy; do not mark old migrations applied speculatively |
| INV-06 | Production schema guard checks only selected columns and table presence | Expand only after runtime-required versus feature-specific scope is explicitly modelled |
| INV-07 | Migration 004 adds an eligibility index not present in the primary bootstrap definition | Verify actual query plans and intended index before reconciling |
| INV-08 | Migration 007 audit verifies table columns, types, PKs, FKs and indexes; primary production guard does not | Reuse or centralize validation rules only after testing cross-dialect behaviour |

## 6. Scope boundary

Package 1A adds only this inventory and static consistency tests. It does not:

- create a migration runner;
- alter `database.py` or any existing migration;
- apply, fake, stamp, rollback or reorder migrations;
- connect to local, Aiven or production databases;
- delete legacy tables or files;
- change runtime behaviour.

The next package can use this inventory to prepare a safe fresh-install and upgrade design for explicit review.


---

## 7. Current manifest, ledger and adoption status — reconciled 17 November 2026

**This section supersedes older tracking statements above where they conflict.** The table in Section 1 remains a useful script-level inventory, but its tracking notes predate the migration-ledger adoption work merged through PR #38.

### 7.1 Manifest at the reviewed master commit

The current `question_bank/migrations/manifest.py` contains these entries:

| Migration ID | File | Execution type | Declared dependency |
|---|---|---|---|
| `001_question_bank_foundation` | `001_question_bank_foundation.sql` | `mysql_client` | None |
| `002_canonical_question_ingestion` | `002_canonical_question_ingestion.sql` | `mysql_client` | 001 |
| `003_canonical_math_taxonomy` | `003_canonical_math_taxonomy.py` | `python` | None |
| `004_student_registration_subject` | `004_student_registration_subject.sql` | `mysql` | None |
| `005_curriculum_question_reuse` | `005_curriculum_question_reuse.py` | `python` | 004 |
| `006_exam_monitoring_mode` | `006_exam_monitoring_mode.py` | `python` | None |
| `008_migration_ledger_upgrade` | `008_migration_ledger_upgrade.py` | `python` | None |

Migration 007 is **not present in this manifest** at the reviewed commit. The reason and intended future treatment are not established by the manifest itself. Do not add it, adopt it, or execute it as part of documentation work.

### 7.2 Ledger support

- `ledger.py:read_ledger(engine)` reads ledger rows and validates the minimum legacy ledger structure.
- `ledger.py:record_migration(...)` writes or updates a ledger row and requires the extended ledger columns. It is not a read-only helper.
- Valid ledger statuses in the helper are `pending`, `running`, `applied`, `failed` and `adopted`.
- The ledger utility does not, by itself, prove that a migration's schema/data postconditions are correct.

### 7.3 Read-only adoption verification

`adoption.py:inspect_legacy_migrations(engine)` classifies each requested migration using schema/data postcondition checks and any available ledger metadata. Its possible states are:

- `VERIFIED_APPLIED`
- `VERIFIED_NOT_APPLIED`
- `PARTIALLY_APPLIED`
- `CONFLICTING`
- `UNKNOWN`

The verifier never writes to the database and deliberately reports `UNKNOWN` when schema inspection cannot prove data effects. A legacy ledger row without a checksum cannot establish source identity; a conflicting checksum or contradictory postconditions can change the classification to `CONFLICTING`.

### 7.4 Migration 008

`008_migration_ledger_upgrade.py`:

- Preserves the legacy `migration_id` and `applied_at` ledger contract.
- Validates the legacy ledger definition before adding metadata.
- Adds `status`, `checksum`, `started_at`, `completed_at`, `error_summary` and `execution_version`.
- Requires exactly one explicit CLI mode: `--dry-run` or `--apply`.
- Does not record its own completion in the ledger.

The dry-run path is intended to report the proposed ledger changes without modifying the database. The apply path changes the schema. Neither mode was run for this documentation update.

### 7.5 Important limits

The presence of a manifest, ledger helper and adoption verifier is not proof of a complete migration execution framework or a fresh-install path. Outstanding reconciliation includes:

1. Bootstrap DDL versus migration overlap.
2. MySQL-client scripts using stored procedures and `DELIMITER`.
3. Historical data backfills and seed effects.
4. Manifest coverage, including the separately existing migration 007.
5. Production and local schema state, which must be inspected independently and only with explicit approval.
6. A safe, tested ordering and rollback/recovery strategy.

### 7.6 Operational boundary

This is a static repository inventory only. No local, Aiven or production database was accessed. No migration, dry-run, adoption check, ledger write, schema bootstrap, seed or rollback was executed. Do not use this document as an instruction to run migrations.
