# Improvia documentation index

This is the central map for repository documentation. Start here rather than searching the repository root.

## Which document is authoritative?

| Topic | Primary reference | How to use it |
|---|---|---|
| Repository work rules | [ChatGPT instructions](CHATGPT_INSTRUCTIONS.md), [AGENTS.md](../AGENTS.md) | Binding workflow, approvals, security and testing constraints |
| Product workflow | [Canonical product workflow](product/PRODUCT_WORKFLOW.md) | Intended assessment-to-improvement journey |
| Product scope | [Product strategy](product/PRODUCT_STRATEGY.md) and root [README](../README.md) | Current launch focus; see proposal warning below |
| Implementation status | [Platform verification](engineering/PLATFORM_VERIFICATION.md) | Distinguishes code, CI, local verification and production evidence |
| Repository audit | [Development audit](engineering/DEVELOPMENT_AUDIT.md) | Read-only findings and current verification priorities |
| Application architecture | [Production architecture reference](architecture/PRODUCTION_ARCHITECTURE.md) | Previously documented topology; not a deployment instruction |
| Database design | [Database schema and architecture](architecture/DATABASE_SCHEMA_AND_ARCHITECTURE.md) | Existing schema observations and design gaps |
| Migration details | [Migration inventory](database/MIGRATION_INVENTORY.md) | Script dependencies and execution boundaries |
| Student access and private media | [Deployment runbook](deployment/IMPROVIA_STUDENT_ACCESS_AND_PRIVATE_MEDIA_RUNBOOK.md) | Prepared procedure; production execution requires separate approval |
| Local setup | [Quick start](operations/QUICK_START.md) | Local-only environment and test safety |
| Registration and eligibility | [Registration reference](operations/STUDENT_REGISTRATION_ELIGIBILITY.md) | Registration and enrollment design |
| Question bank | [Question-bank documentation](question-bank/README.md) | Curriculum, extraction and ingestion references |
| Tuition operations | [Tuition documentation](tuition/README.md) | Separate tuition-centre planning documents |
| Testing | [Testing guidance](testing/README.md) | Verification approach and evidence requirements |
| Security and privacy | [Security guidance](security/README.md) | Student-data handling and release checks |

## Folder map

- `product/` — strategy, scope, workflow, commercial roadmap and evaluation design.
- `engineering/` — current repository audit and implementation/release verification.
- `architecture/` — application and database architecture.
- `database/` — migration inventory and database operational notes.
- `security/` — privacy and access-control guidance.
- `deployment/` — deployment and private-media runbooks.
- `operations/` — local setup, registration and operating procedures.
- `question-bank/` — curriculum, ingestion, extraction and research workflows.
- `testing/` — test execution and evidence standards.
- `tuition/` — separate tuition-centre planning.
- `history/` — dated audits, progress snapshots, superseded plans and branch-only artifacts.

## Important scope and status rules

1. The approved initial Improvia focus is CBSE/ICSE Mathematics Classes 10–12. The expanded curriculum document under `product/proposals/` records a proposal, not an approved launch expansion.
2. Technical support for additional subjects/classes does not establish validated content or commercial launch approval.
3. Documents under `history/` preserve context. They are not current operating instructions unless the index explicitly says otherwise.
4. Branch-only artifacts are labelled with their source branch/PR and evidence status. Their presence here does not mean their code or feature is on `master`.
5. A code path, test, green CI run, local manual verification and production verification are separate evidence levels.
6. Never use an archived migration command or runbook against a live database without checking current migration history, code and an approved plan.

## Module documentation kept beside code

Some documentation intentionally remains next to its module so it is discoverable during code changes:

- [Database module README](../database/README.md)
- [Question-bank README](../question_bank/README.md)
- [Question-bank agent README](../question_bank/agents/README.md)
- [AI extraction schema](../question_bank/extraction/AI_EXTRACTION_SCHEMA.md)
- [Extraction review schema](../question_bank/extraction/review_schema.md)
- [Shaalaa extractor README](../shaalaa_extractor/README.md)
- [GitHub instructions](../.github/instructions/Instruct.instructions.md)

## Maintenance rule

When implementation changes, update the relevant authoritative document and this index if ownership or location changes. Do not create another status summary when the existing verification/audit document can be updated. Preserve dated snapshots in `history/`; do not silently overwrite historical findings.
