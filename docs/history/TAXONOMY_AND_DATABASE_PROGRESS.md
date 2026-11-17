# Taxonomy and Database Progress — 2026-09-26

## Completed

The canonical mathematics syllabus taxonomy has been validated and deployed to both the local development database and the Aiven production database.

### Taxonomy version

`2026.27.4`

### Scope

- Mathematics
- Applied Mathematics (CBSE, Classes XI–XII, Subject Code 241)
- CBSE Classes X–XII
- ICSE Class X
- ISC Classes XI–XII
- Academic year: 2026–27

### Deployed taxonomy counts

| Item | Count |
|---|---:|
| Subjects | 2 |
| Canonical chapters | 88 |
| Syllabus units | 62 |
| Syllabus mappings | 133 |
| Applied Mathematics canonical chapters | 31 |
| Review-required units | 0 |
| Review-required mappings | 0 |

## Database verification

The migration was first validated with a dry-run against local MySQL and then against Aiven MySQL.

The migration was subsequently applied independently to both databases.

### Local MySQL

Verified after apply:

- `canonical_chapters`: 88
- `syllabus_units`: 62
- `syllabus_chapters`: 133
- Applied Mathematics chapters: 31

### Aiven MySQL

Verified after apply:

- `canonical_chapters`: 88
- `syllabus_units`: 62
- `syllabus_chapters`: 133
- Applied Mathematics chapters: 31

Existing question records were not modified by the taxonomy migration.

## Taxonomy design

The taxonomy is additive. It introduces:

- `canonical_subjects`
- `canonical_chapters`
- `syllabus_units`
- `syllabus_chapters`

The existing `chapters` table and existing question records were intentionally left intact.

The subject dimension is explicit, so Mathematics and Applied Mathematics cannot be treated as the same question bank.

## Important architecture decision

Local MySQL and Aiven MySQL remain separate environments. The taxonomy was applied independently to each database; this is not continuous local-to-Aiven replication.

Aiven remains the production source of truth for the application.

## Current project status

The platform has now completed:

1. Canonical question-ingestion foundation.
2. AI JSON → review → canonical question pipeline.
3. Optional question-bank primary-to-secondary sync layer.
4. Production Aiven architecture documentation.
5. Canonical Mathematics + Applied Mathematics syllabus taxonomy.
6. Taxonomy deployment and verification in local and Aiven MySQL.

### Next priority

Connect the existing student registration flow to the new subject-aware taxonomy and verify that a student selecting Mathematics or Applied Mathematics is routed only to the correct subject-specific assessments.

Do not introduce AI grading or complex adaptive testing before the controlled assessment → evaluation → diagnosis → report loop is validated with real students.
