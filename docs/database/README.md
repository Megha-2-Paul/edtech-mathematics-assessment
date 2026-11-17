# Database documentation

- [Schema and architecture reference](../architecture/DATABASE_SCHEMA_AND_ARCHITECTURE.md) — schema observations, design constraints and known gaps.
- [Migration inventory](MIGRATION_INVENTORY.md) — migration scripts, dependencies, effects and execution notes.
- [Aiven migration 005 audit](../history/branch-artifacts/AIVEN_MIGRATION_AUDIT.md) — historical read-only audit procedure from an earlier branch; verify current migration history before reuse.

## Safety

Local development, CI and production databases are separate environments. Use disposable local/CI databases for tests. Do not run migrations, schema initialization, seed scripts or destructive writes against Aiven/production without a separately approved plan, verified backup/restore path and current code-level migration audit. Never place credentials or full database URLs in documentation.
