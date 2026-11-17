# Testing and verification

## Evidence levels

1. **Implemented in repository:** source or tests exist.
2. **CI-verified:** a named workflow passed on a specific commit and configured environment.
3. **Locally verified:** the owner ran the application/tests against an isolated local database and manually checked the workflow.
4. **Production-verified:** live configuration, access controls, backup/restore and real deployment behavior were explicitly checked.

Do not promote a feature from one level to another without evidence.

## Required testing principles

- Inspect pytest configuration, fixtures, imports and database side effects before running tests.
- Never point tests at production/Aiven.
- Use synthetic student data and images.
- Run the relevant targeted tests and the core exam-platform integration/smoke tests.
- Verify access boundaries, uploads, timers, duplicate submissions, partial evaluation and attempt state.
- Compare report calculations against hand-calculated reference cases.
- Test migrations on disposable MySQL, including repeat/idempotency behavior where applicable.
- Never delete, skip or silently exclude a failing test to make CI green.

See [Platform verification](../engineering/PLATFORM_VERIFICATION.md), [repository instructions](../CHATGPT_INSTRUCTIONS.md) and [migration inventory](../database/MIGRATION_INVENTORY.md). Record exact commands, results, commit and environment; passing unit tests alone does not prove production readiness.
