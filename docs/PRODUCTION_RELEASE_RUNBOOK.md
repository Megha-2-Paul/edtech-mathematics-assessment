# Improvia production release and database runbook

## Safety boundaries

- Do not merge code that can trigger a Render auto-deploy until the production database prerequisites and Render deployment behaviour are confirmed.
- Do not run a production migration without an approved backup, a reviewed dry-run/audit, and explicit approval.
- Never paste database URLs, credentials, student records, passwords, or activation tokens into GitHub issues or chat.
- Keep the current production application available until the release candidate has passed isolated CI and the migration plan is approved.

## Required migration order

1. Confirm the current Render deployment commit and whether merging to `master` automatically deploys.
2. Take an Aiven backup/snapshot and verify that the backup is restorable.
3. Run the read-only audit in PR #28 for migration 005. Review missing tables/columns, enrollment backfill counts, and unmatched question mappings.
4. Review and explicitly approve migration 005. Apply it only with the reviewed command from `docs/AIVEN_MIGRATION_AUDIT.md`.
5. Run the new migration 006 in read-only mode first:
   `python question_bank/migrations/006_student_access.py --database-url "$DATABASE_URL"`
6. Review the output and approve the schema change before running:
   `python question_bank/migrations/006_student_access.py --database-url "$DATABASE_URL" --apply`
7. Verify that both access tables and their required columns exist. Do not create production tables automatically during app startup.
8. Deploy the reviewed application only after schema verification and passing CI.

## Backup and rollback

- Before any migration, record the current deployment commit and capture an Aiven backup/snapshot. Confirm recovery steps with the provider console.
- Migration 006 creates only two tables and does not rewrite student, test, attempt, or evaluation records.
- If the application release needs to be rolled back, redeploy the previous application version and leave the two new tables in place. Do not drop them automatically; they may contain activation and credential records.
- If migration 005 causes unexpected data changes, stop further releases and use the reviewed backup/restore procedure. Do not attempt an improvised reverse migration against live student data.
- After rollback, verify registration, exam attempts, uploads, teacher evaluation, and report access before reopening student access.

## Student access onboarding

- Only approved/enrolled active students may be issued an activation link.
- The teacher/operator calls the authenticated `POST /teacher/students/<student_id>/access-link` endpoint and sends the returned URL privately to the intended student.
- Activation links expire after 24 hours and can be used once. Only a hash of each token is stored.
- The student chooses a password of at least 12 characters. Login attempts are temporarily locked after five consecutive failures.
- Reissue a link through the authenticated teacher endpoint if the student loses access. Do not ask students to send passwords over WhatsApp.

## Release acceptance evidence

Record the commit SHA, CI run URL, pass/fail status for every end-to-end scenario, database audit output with credentials removed, and the live deployment version after deployment. Any check that cannot be run against the real deployment must be marked unverified rather than passed.
