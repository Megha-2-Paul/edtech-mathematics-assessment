# Aiven Migration 005 Audit Runbook

## Purpose

Validate the live Aiven database before applying migration 005. The audit is strictly read-only.

## Preconditions

- Run from a local checkout of this repository.
- The local `.env` must contain the existing Aiven connection settings used by the project.
- Do not paste the database URL, username, or password into chat or commit it to Git.

## 1. Run the read-only audit

PowerShell:

```powershell
python question_bank/migrations/005_curriculum_question_reuse_audit.py `
  --database-url "$env:DATABASE_URL" `
  --taxonomy curriculum_taxonomy_2026_27.json `
  --json-out aiven_migration_005_audit.json
```

If this project exposes the Aiven URL through `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD` instead of `DATABASE_URL`, construct the URL locally without printing it.

## 2. Equivalent migration dry-run

```powershell
python question_bank/migrations/005_curriculum_question_reuse.py `
  --database-url "$env:DATABASE_URL" `
  --taxonomy curriculum_taxonomy_2026_27.json `
  --dry-run
```

This invokes the same read-only audit. It does not create tables or change rows.

## 3. Send the audit output for review

Share only the terminal output or the generated JSON contents that do not contain credentials or connection strings.

The important sections are:

- Missing target tables
- Missing legacy columns
- Existing target-table row counts
- Eligible student registrations and board/class/subject distribution
- Eligible questions
- Predicted exact mappings
- Unmatched question groups

## 4. Production apply

Do **not** run `--apply` until the audit has been reviewed.

```powershell
python question_bank/migrations/005_curriculum_question_reuse.py `
  --database-url "$env:DATABASE_URL" `
  --taxonomy curriculum_taxonomy_2026_27.json `
  --apply
```

Then run the post-migration verification queries/tests before using the new curriculum model in production.