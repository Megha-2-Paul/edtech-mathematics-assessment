# PR #31 / PR #28 Reconciliation and First Cleanup Pass

**Working branch:** `feature/v1-performance-report`  
**Related PRs:** [#31 V1 hardening](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/31), [#28 migration audit](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/28)  
**Work date:** 25 October 2026  
**Status:** Code changes committed to the PR #31 branch; automated CI was still running at the time this note was written. Do not treat this note as a production release approval.

## Objective

Reconcile the overlapping V1 hardening and migration-audit work into one tested implementation, fix the identified privacy/storage and migration-audit defects, and begin conservative branch/PR cleanup. Reducing the PR count is not the goal by itself.

## Changes made on `feature/v1-performance-report`

### 1. Answer-image storage now uses the storage abstraction

- The upload handler calls `exam_platform.media.store_image()` instead of unconditionally saving files directly from the route.
- The configured application upload folder is passed into the local fallback, so local storage and the app's configured folder agree.
- Cloudinary deployments use the existing authenticated Cloudinary storage path; the handler stores the returned storage reference rather than assuming a local filesystem path.
- If image storage or database persistence fails, the route logs the failure, attempts to clean up any stored object, and returns a retryable service error rather than reporting a successful upload.
- Image deletion uses the matching media-storage helper, including Cloudinary assets, instead of calling `os.remove()` on every stored reference.

**Deployment caveat:** the local filesystem fallback is for local/test use unless a persistent disk is configured. Production must have working Cloudinary credentials or another deliberately configured durable storage backend. This code change does not verify the live provider configuration.

### 2. Removed the unauthenticated public upload route

- Removed `/uploads/<path:filename>`, which served raw answer images without ownership checks.
- Student retrieval remains through the attempt/image endpoint, which performs attempt access checks.
- The end-to-end smoke tests now expect the raw upload URL to return 404 because the route should not exist.
- The existing smoke suite continues to cover owner image retrieval, teacher-proxy authorization, and cross-student access denial.

### 3. Corrected canonical concept identity in migration 005

- Added `canonical_concept_id(subject_id, chapter_name)` so a chapter slug is scoped to its canonical subject.
- This avoids treating identical chapter names in different subjects as equivalent solely because their text matches.
- Chapter aliases that intentionally normalize to the same slug within one subject continue to resolve to the same concept ID.
- The migration inserts the subject-scoped concepts before updating chapter references. Existing old concept rows are not automatically deleted; cleanup of unused legacy concepts is deliberately non-destructive and can be considered after a data audit.
- Added regression coverage for subject-scoped IDs and within-subject aliases.

**Migration caution:** this changes the IDs assigned by migration 005 for canonical concepts. Before running it against production, take/verify a backup, run the read-only audit, inspect existing concept/chapter references, and review the expected row changes. Do not run `--apply` against Aiven just because CI passes.

### 4. Corrected question-to-curriculum mapping ambiguity

- The migration now resolves a question's curriculum through its board, class, academic year, and subject display name associated with that curriculum, rather than joining the subject catalog by display name alone.
- The migration only backfills an exact question mapping when that board/class/display-name context identifies exactly one canonical subject ID.
- This avoids ambiguous mapping when display names such as **Computer Applications** or **Computer Science** appear for multiple board-specific subject IDs.

### 5. Corrected migration audit counts and subject lookup

- `expected_enrollment_inserts` is no longer a copy of the eligible-registration count.
- The audit counts eligible active registrations that lack the corresponding 2026–27 enrollment, using a `NOT EXISTS` check over student, board, class, subject ID, and academic year.
- If the enrollment table is absent, all eligible rows are reported as expected inserts. If the table exists but required columns are missing, the audit reports the count as unavailable instead of pretending it is exact.
- The audit now resolves a subject through `(board, class, display name)` to canonical subject IDs, rather than using a single dictionary keyed only by display name.
- Ambiguous board/class/subject contexts are surfaced as not-mappable instead of being silently assigned to whichever duplicate name appeared last.

### 6. Regression tests added/updated

- Added a local media-storage lifecycle test: configured folder, read-back, content type, and deletion.
- Updated the end-to-end smoke test to require that raw answer-image URLs do not exist.
- Added tests for subject-scoped canonical concept IDs and alias preservation.
- Added tests for board/class disambiguation of duplicate display names.
- Added an SQLite-backed audit test showing that existing enrollments are not counted as new inserts.
- Added a source-level regression check for the migration's board/class/subject disambiguation.

## PR #28 disposition

PR #28 was closed as **superseded, not merged** after its four changed files were confirmed to be present in PR #31:
- `docs/AIVEN_MIGRATION_AUDIT.md`
- `question_bank/migrations/005_curriculum_question_reuse.py`
- `question_bank/migrations/005_curriculum_question_reuse_audit.py`
- `tests/test_curriculum_taxonomy_2026_27.py`

The close comment records that the work is retained in PR #31 and that production migration work has not been run. PR #31 remains the single integration path for this work.

## CI and validation status

The code changes triggered GitHub Actions workflow **Tests**. The first run [#40138825786](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/actions/runs/40138825786) passed on commit `c7d427127e05bfd18934a75ec2e61dd75789fbd6`. The latest run [#40138939766](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/actions/runs/40138939766) also completed with **success** on commit `e7c8f0272d5a3bdfedef43ee132fa40bf9d8d5aa`, including the audit-output clarification. This is the current code-validation evidence for the fixes in this pass. Recheck the current PR status before merge because subsequent commits or environment changes can invalidate the result.

CI against an isolated MySQL database does not verify:
- live Aiven schema and existing data;
- backup/restore readiness;
- live Render environment settings or auto-deploy behavior;
- production Cloudinary credentials and authenticated asset delivery;
- real student/guardian acceptance of the report.

## First branch-cleanup pass

### Completed
- Closed PR #28 as superseded after porting/reconciling its useful files into PR #31.
- Kept PR #31 as the one active V1 hardening/migration integration path.

### Intentionally left open / untouched
- **PR #32** Groq question-ingestion prototype: do not merge until the real-PDF benchmark is complete.
- **PR #4 and #5** URL ingestion / Shaalaa parser: remain separate from this pass; preserve their stacked dependency and resolve in order.
- **PR #6** MarkItDown PDF extraction: do not merge merely to reduce the count; verify supersession by merged PR #8 before any closure/deletion.
- **PR #9** cloud-to-local question-bank sync and its base branch `question-bank-dual-sync`: do not merge until the need for a second sync architecture is decided.
- **PR #24** JSON error-guidance v2: retain for a later focused review.

### Safe branch-deletion shortlist carried forward

These branches were previously identified as candidates for deletion after rechecking current refs and dependencies:

**Merged-PR heads reported to match their merged PR heads:**
- `curriculum-multi-board-question-reuse`
- `stage-4-taxonomy-applied-math`
- `stage-5-registration-eligibility`
- `stage-6-google-registration-pipeline`
- `docs/expanded-school-subject-scope`
- `docs/extraction-audit-status`
- `docs/production-registration-architecture`
- `dual-db-sync`
- `feature/question-extraction`
- `schema-v2-canonical-question-ingestion`
- `fix-review-app-syntax`
- `fix-review-app-remaining-syntax`
- `fix-review-app-persistent-helper-order`
- `stage-7-google-registration-webhook-v2`
- `stage-8-extraction-hardening`
- `stage-8-json-contract`
- `improve-sequential-extraction-review`

**Reported to have zero unique commits relative to master:**
- `fix-json-error-guidance`
- `stage-1-question-ingestion`
- `stage-2-pdf-ingestion`
- `v1.3-canonical-question-bank`

Before deleting any branch, recheck its latest head, whether any open PR uses it as a head or base, and whether it contains useful work not retained elsewhere.

### Deletion limitation for this pass

The connected GitHub actions available in this session can inspect refs and update files/PR state, but do not expose a branch-ref deletion action. Therefore **no branch ref was deleted by this pass**. PR #28 was closed, but `audit-curriculum-migration` still needs deletion after a fresh safety check through GitHub's branch UI or another authorized Git operation. Do not interpret the candidate list as completed deletions.

## Next actions

1. Wait for and inspect the latest PR #31 CI result; fix failures and rerun.
2. Recheck PR #31 mergeability and changed files.
3. Run the read-only migration audit against Aiven locally and review its output without sharing credentials.
4. Review the concept-ID changes and expected affected rows before any production apply.
5. Verify production storage configuration and backup/restore path.
6. Merge/deploy only after CI, code review, and the production release gate are satisfied.
7. Use GitHub branch management to delete only verified redundant branches; do not merge ingestion/sync PRs merely to lower the count.
