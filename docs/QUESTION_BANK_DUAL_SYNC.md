# Question Bank Dual Sync

The platform can optionally dual-write **approved JSON-imported questions** to both the local MySQL database and the cloud MySQL database.

## Local workflow

Run the teacher application from VS Code/local Flask and configure:

```env
QUESTION_BANK_SYNC_DATABASE_URL=<cloud MySQL SQLAlchemy URL>
```

Keep the value only in the local `.env` file. Never commit credentials.

Then:

1. Import the JSON through the local teacher panel.
2. Review and edit the extracted questions.
3. Approve a question.
4. The application writes the canonical question to the cloud database first.
5. If the cloud write succeeds, it writes the same question to the local database.
6. If cloud sync is unavailable, approval fails instead of silently creating a local-only question.

Only the question-bank record is dual-written. Student attempts, evaluations, payments, and other application data remain local.

## Render

The deployed Render application continues to use its normal cloud `DATABASE_URL`. It does not need the secondary-sync variable.

This means the local teacher panel becomes the controlled enrichment tool when dual sync is enabled. The Render teacher panel remains available for normal production administration.

## Important limitation

This is intentionally an **approved-question dual-write**, not a general database replication system. It does not synchronize arbitrary local/cloud changes.

If a question is edited manually later in the local Question Bank, that edit is not automatically mirrored unless the edit path is explicitly extended to use the same dual-write flag.

## Safety

The cloud database is written first during dual-sync approval. This prevents a local question from appearing published when the cloud write failed.

The feature is opt-in: without `QUESTION_BANK_SYNC_DATABASE_URL`, existing behavior is unchanged.
