# Improvia — Student Access Migration and Private Media Deployment Runbook

**Scope:** F-01 deployment migration and F-02 private Cloudinary media handling
**Migration:** `question_bank/migrations/007_student_access.py`
**Status:** Operational procedure prepared; production execution not approved
**Audience:** Repository maintainer / deployment operator

---

## 1. Purpose and safety rules

This document describes the controlled deployment procedure for the student-access schema and private answer-image storage.

It does not authorise production database changes, Cloudinary asset changes, application deployment, or deletion of existing media.

### Non-negotiable requirements

1. Preserve existing student records, assessment attempts, answers and uploaded images.
2. Do not run the migration against production before a verified backup exists.
3. Do not assume a successful backup job means the backup is restorable.
4. Do not expose database credentials, Cloudinary secrets, signed URLs or student data in logs or chat.
5. Do not drop or recreate existing access tables to resolve schema discrepancies.
6. Do not delete legacy Cloudinary assets during migration.
7. Do not deploy application code that requires the new access tables before the migration is verified.
8. Stop if the live schema or media inventory differs from the assumptions in this runbook.
9. Keep a record of commands, timestamps, operator, results and approvals without recording secrets.

### Approval gates

| Operation | Separate approval required |
|---|---|
| Read-only production schema audit | Yes, including permission to access production |
| Production backup creation | Yes |
| Production migration 007 | Yes |
| Cloudinary asset inventory | Yes |
| Cloudinary asset migration or re-upload | Yes |
| Updating production media references | Yes |
| Deleting old media | Yes |
| Production application deployment | Yes |

---

## 2. F-01 — Student-access migration

### 2.1 What migration 007 creates

The migration creates two MySQL tables:

**`student_access_credentials`**

- `student_id` primary key
- `password_hash`
- `failed_login_count`
- `locked_until`
- `last_login_at`
- `created_at`
- `updated_at`
- Foreign key to `students.student_id` with `ON DELETE CASCADE`

**`student_access_tokens`**

- `token_hash` primary key
- `student_id`
- `expires_at`
- `used_at`
- `created_at`
- Foreign key to `students.student_id` with `ON DELETE CASCADE`
- Index `idx_student_access_token_student`
- Index `idx_student_access_token_expiry`

The migration expects the parent `students.student_id` column to be `VARCHAR(32)`.

It creates the access tables; it is not a student-data import or password-reset operation.

### 2.2 Pre-migration repository checks

Before deployment:

- Confirm the intended deployment branch and commit.
- Confirm `007_student_access.py` is present in the deployed source.
- Confirm the old `006_student_access.py` filename is not referenced by application code or tests.
- Confirm the production Python and SQLAlchemy dependencies are installed.
- Confirm the production database engine is MySQL and the migration is being run against the intended database.
- Confirm the application version expects the two student-access tables.
- Confirm the database is not being modified by another migration or deployment process.

Do not infer the production schema from the local development database.

### 2.3 Backup and restore verification

A backup is mandatory before migration.

1. Identify the exact production database and its provider.
2. Create a full backup using the provider's supported backup/export mechanism.
3. Record the backup identifier, timestamp, database identity and operator.
4. Confirm the backup completed successfully.
5. Restore the backup into a separate, isolated database or instance.
6. Verify that the restored database is readable and contains the expected application tables.
7. Verify representative student, assessment and answer records.
8. Record the restore verification result.
9. Restrict access to the backup because it contains student information.

A backup is not considered verified merely because an export file exists.

**Stop condition:** if the backup cannot be restored and checked, do not apply migration 007.

### 2.4 Read-only schema audit

First, inspect the migration's audit behaviour and ensure the intended database URL is configured securely.

The migration defaults to read-only audit mode unless `--apply` is explicitly supplied.

From the repository root:

```powershell
.\.venv\Scripts\python.exe .\question_bank\migrations\007_student_access.py
```

This command uses `DATABASE_URL` from the process environment.

Before running it, verify locally that `DATABASE_URL` points to the intended target. Never paste its value into logs, screenshots or chat.

Review the report for:

- Existence of the `students` parent table.
- `students.student_id` type and length.
- Existing student-access tables.
- Missing or incompatible columns.
- Primary-key correctness.
- Foreign-key references and cascade behaviour.
- Required indexes.

The audit is read-only.

**Stop conditions:**

- Parent table or parent key is missing.
- Parent key type is incompatible.
- An existing access table has an unexpected structure.
- A foreign key or index is missing or incompatible.
- The target database identity is uncertain.

Do not attempt to fix these conditions by dropping tables or changing production data without a separate reviewed remediation plan.

### 2.5 Migration approval and execution

Only proceed when all of the following are true:

- A restorable production backup has been verified.
- The schema audit has been reviewed.
- The target database has been positively identified.
- The application release requiring migration 007 is approved.
- A maintenance and rollback plan is agreed.
- The operator has explicit approval to write to the production database.

The migration's write mode is:

```powershell
.\.venv\Scripts\python.exe .\question_bank\migrations\007_student_access.py --apply
```

This command performs database writes. It must not be run against production without the approvals above.

The migration uses MySQL DDL. MySQL DDL statements can commit independently of application transaction expectations. Do not assume the migration can be rolled back by simply rolling back a transaction.

### 2.6 Post-migration verification

The migration performs a schema audit after applying its DDL.

Additionally verify:

- Both access tables exist.
- Required columns and data types match the migration specification.
- Primary keys are correct.
- Foreign keys reference the expected student key.
- Cascade rules are correct.
- Required token indexes exist.
- Existing student records and unrelated application tables remain intact.
- No unexpected database errors occurred.

If verification fails:

1. Stop deployment.
2. Preserve logs and the migration result.
3. Do not repeatedly rerun the migration as a repair strategy.
4. Do not drop partially created tables.
5. Compare the actual schema with the expected schema.
6. Obtain approval for a forward repair or a restore-based recovery.

### 2.7 Deployment sequence

The intended order is:

1. Verify backup and restore.
2. Complete the read-only schema audit.
3. Obtain migration approval.
4. Apply migration 007.
5. Verify the resulting schema.
6. Deploy the application version that depends on the new schema.
7. Run approved smoke tests.
8. Monitor logs, authentication failures and database errors.

Do not deploy the dependent application version before the required schema is ready.

---

## 3. F-02 — Private Cloudinary media policy

### 3.1 Intended storage behaviour

The current media implementation:

- Uploads new Cloudinary answer images with `type="authenticated"`.
- Stores a `cloudinary://` reference rather than exposing a direct provider URL.
- Generates signed HTTPS authenticated delivery URLs for retrieval.
- Reads image bytes through the application's access-controlled route.
- Does not fall back to public Cloudinary delivery if authenticated retrieval fails.
- Raises an error when authenticated retrieval fails or returns an empty response.

Local media is resolved inside the configured upload directory. Path traversal outside that directory is rejected.

The application should not expose Cloudinary delivery URLs directly to students or unauthorised users.

### 3.2 Legacy media compatibility

Older assets may have been uploaded with Cloudinary delivery type `upload` (public delivery).

The current read implementation deliberately does not fall back to public delivery.

Consequently:

- A legacy public-only asset may not be retrievable through the current private proxy.
- Do not assume that all existing media is authenticated.
- Do not assume legacy public assets exist until the inventory is completed.
- Do not restore public-read fallback to make old images work.
- Do not delete old media merely because authenticated retrieval fails.

The approved policy is to migrate or re-upload legacy media into authenticated delivery before it is served through the private proxy.

### 3.3 Legacy asset inventory

Before changing Cloudinary assets:

1. Obtain approval for a read-only inventory.
2. Identify the actual database tables and columns that store answer-image references.
3. Identify all relevant application environments and Cloudinary accounts.
4. Export the relevant media references securely.
5. Classify each asset as:
   - Authenticated and retrievable.
   - Public-only legacy asset.
   - Missing or unavailable.
   - Unknown or unverified.
6. Preserve the relationship between each asset and its student, attempt and answer.
7. Record counts and exceptions without exposing student personal information.

Do not guess table names or issue database queries against an unverified schema. Inspect the current schema and repository data model first.

Do not assume a Cloudinary asset's delivery type based only on its application reference string.

### 3.4 Migration or re-upload procedure

For every confirmed legacy public-only asset:

1. Preserve the original asset and its existing reference.
2. Retrieve the original image through an authorised migration process.
3. Validate that the retrieved file is non-empty and is a supported image.
4. Upload it to Cloudinary using authenticated delivery.
5. Use a stable, collision-safe asset identifier.
6. Verify authenticated retrieval of the new asset.
7. Verify the content matches the original.
8. Update the relevant application reference only after the new asset is verified.
9. Confirm the application can serve the image through its private access-controlled route.
10. Record the old and new references in a restricted migration record.

Do not update database references before the new authenticated asset has been verified.

Do not overwrite existing assets unless the migration plan explicitly guarantees that the original remains recoverable.

### 3.5 Deletion precautions

The current `delete_image()` implementation first attempts deletion as an authenticated Cloudinary asset and, if the provider reports `not found`, attempts deletion using the legacy `upload` type.

This behaviour is relevant to legacy cleanup.

Therefore:

- Do not use `delete_image()` as part of the migration or inventory process.
- Do not run bulk deletion based on failed authenticated retrieval.
- Confirm the exact asset type and reference before deletion.
- Verify that the new authenticated asset works and the database points to it.
- Retain the original until the migration is accepted and the retention policy permits deletion.
- Obtain explicit approval before deleting old Cloudinary assets.

### 3.6 Media verification tests

The repository has regression tests covering:

- Authenticated HTTPS Cloudinary retrieval.
- Signed URL parameters.
- Retrieval failure handling.
- Empty response rejection.
- Local upload path restrictions.

Run the relevant tests before deployment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_media_storage.py -q
```

Also verify the teacher image route and its access checks:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_teacher_auth.py tests/test_teacher_answer_image_route.py -q
```

These tests do not prove that every production Cloudinary asset is migrated. A separate approved inventory and verification process is required.

---

## 4. Rollback and incident response

### 4.1 Migration failure

If migration 007 fails:

- Stop the deployment.
- Preserve the exact error and migration logs.
- Do not repeatedly execute `--apply`.
- Inspect the actual database schema using read-only operations.
- Determine whether any DDL statements were committed.
- Compare the schema with the pre-migration backup.
- Decide between a reviewed forward repair and restore-based recovery.

Because MySQL DDL may commit independently, do not assume a transaction rollback restored the original schema.

Never drop the new tables automatically. They may contain data if the migration was partially executed or retried.

### 4.2 Application deployment failure

If application deployment fails after migration:

- Keep the migration tables intact.
- Restore the previous application release if that is the approved recovery strategy.
- Confirm the previous release can safely operate with the additional tables.
- Review logs and verify student, assessment and answer workflows.
- Do not reverse the schema change without a separate impact assessment.

### 4.3 Media migration failure

If a media migration fails:

- Keep the original asset.
- Do not update the database reference to an unverified asset.
- Preserve the previous reference.
- Record the failure and retry only after identifying its cause.
- Do not re-enable public delivery as a workaround.
- Do not delete either asset until recovery is complete and approved.

---

## 5. Post-deployment smoke-test checklist

Complete these checks in an approved test environment before declaring the release ready.

### Database and student access

- [ ] Application connects to the intended database.
- [ ] Student-access tables exist with the expected schema.
- [ ] Existing student records remain available.
- [ ] Student activation workflow works.
- [ ] Activation tokens expire and cannot be reused.
- [ ] Student login works.
- [ ] Invalid login and account lockout behaviour work.
- [ ] Existing assessment history remains accessible.

### Teacher security

- [ ] Teacher routes reject missing credentials when a password is configured.
- [ ] Invalid credentials are rejected.
- [ ] Valid credentials are accepted.
- [ ] Missing teacher password on Render produces the expected configuration failure.
- [ ] Unrelated public routes are not accidentally protected.
- [ ] Private answer images are accessible only through the authorised route.

### Media

- [ ] New answer images upload as authenticated Cloudinary assets.
- [ ] Authenticated retrieval works.
- [ ] The application does not expose direct public media URLs.
- [ ] Unauthorised users cannot retrieve private answer images.
- [ ] Legacy assets have been inventoried and classified.
- [ ] Migrated legacy assets are verified before their references are updated.
- [ ] No legacy asset was deleted prematurely.

### Operations

- [ ] Application logs show no new migration or authentication errors.
- [ ] Backup and recovery records are retained.
- [ ] Deployment version and migration result are recorded.
- [ ] Monitoring and incident ownership are assigned.

---

## 6. Evidence and sign-off record

Complete this record during the actual deployment. Do not fill it with assumed or unverified results.

| Item | Record |
|---|---|
| Repository commit / release | Pending |
| Deployment environment | Pending |
| Database identity (non-secret) | Pending |
| Backup identifier | Pending |
| Backup restore verification | Pending |
| Read-only schema audit | Pending |
| Migration approval reference | Pending |
| Migration 007 execution result | Pending |
| Post-migration schema audit | Pending |
| Cloudinary inventory date | Pending |
| Legacy assets identified | Pending |
| Legacy assets migrated | Pending |
| Media verification result | Pending |
| Application deployment result | Pending |
| Smoke-test result | Pending |
| Operator and reviewer | Pending |

### Final release decision

The release must remain blocked if:

- The backup is not verified.
- The migration schema audit is incompatible.
- Migration 007 has not been approved and verified.
- Required legacy media cannot be retrieved privately.
- Teacher access controls are not configured on the hosted service.
- Critical smoke tests fail.

**Current operational status:** migration execution, production media inventory, media migration and production deployment are not confirmed by this document.