# Repository Audit, Branch Reconciliation, and Next-Work Plan

**Repository:** `Megha-2-Paul/edtech-mathematics-assessment`  
**Audit snapshot:** 25 October 2026  
**Purpose:** Preserve the outcomes of the repository review so work can resume from the same point without repeating the audit.  
**Important status note:** This document records findings and recommendations, not completed code changes. No branches were deleted, no PRs were merged or closed, and no production migration was applied as part of this audit.

---

## 1. Executive summary

The repository contains substantial functionality for the Improvia mathematics assessment workflow: student registration and access, MCQ and subjective exams, answer saving and submission, handwritten-answer uploads, teacher/admin question-bank and test creation, manual marking, reports, error-based recommendations, curriculum/taxonomy work, and question ingestion.

The next task is **release hardening and reconciliation**, not adding more features or starting a platform rewrite.

The three highest-priority areas are:

1. **PR #31 — V1 performance/release hardening:** fix answer-image storage and authorization risks before production use.
2. **PR #28 — curriculum migration audit:** reconcile overlapping migration/audit work with PR #31 and correct audit-count and subject-identity issues.
3. **PR #32 — Groq question ingestion:** keep it as a prototype until it passes a benchmark using real, representative Mathematics PDFs and manually verified expected output.

There are also too many branches. A safe cleanup plan was identified, but **do not delete branches blindly**: preserve useful documentation, resolve stacked PRs correctly, and settle competing question-bank sync designs first.

Commercially, keep the pilot narrow: **CBSE/ICSE Class 10–12 Mathematics**. A broader curriculum schema may be useful technically, but it does not justify launching multiple subjects/classes now. Improvia's differentiator is not “more mock tests”; it is explaining why marks are lost and tracking whether that diagnosis leads to improvement.

---

## 2. PR #31 — `feature/v1-performance-report`

**Status at audit:** Open PR; branch was reported 75 commits ahead of master and zero behind. Its head commit was `97c1423b8f9bcf23febb01b9d016e9db73fe2f3c`. CI run `39837105036` passed.

### Positive work observed

- Password hashing.
- Activation links with expiry.
- Login lockout controls.
- Student route access controls.
- Duplicate/immutable submission protections.
- Recording unanswered responses.
- Guards against missing evaluations and invalid marks.
- PDF performance reports.
- Startup schema guard.
- Isolated MySQL smoke testing, including migrations 005 and 006, application startup, `test_exam_platform.py`, and the rest of the test suite.

The passing CI is meaningful evidence of isolated integration coverage, but it is not proof that the live production database, deployment storage, or all report edge cases are safe.

### Blocker A — uploaded answer images are saved locally

The upload route in `exam_platform/app.py` saves a file directly to a local `uploads/` path and stores that path. It does not call `store_image()` from `exam_platform/media.py`, even though authenticated/cloud media storage was introduced.

**Why it matters:** on a deployment such as Render, local disk can be ephemeral unless persistent storage is explicitly configured. A restart, redeploy, or instance change can make uploaded answer images disappear. That undermines subjective assessment and evidence retention.

**Required follow-up:**
- Trace the full upload path from request validation through storage, database persistence, retrieval, and deletion.
- Integrate the intended persistent/cloud storage abstraction, or explicitly configure and test a persistent disk if that is the chosen design.
- Avoid persisting environment-specific local absolute paths as the only reference.
- Add tests for upload, retrieval after app restart/reinitialization, invalid file handling, and provider/storage failures.
- Verify the behavior with deployment configuration, not only a local test client.

### Blocker B — direct public `/uploads/<path:filename>` serving

A route directly serves files under `/uploads/` without ownership/authentication checks. Student answer images are private assessment material. If a filename or URL is discovered, direct serving may bypass the authenticated image endpoint.

**Required follow-up:**
- Remove or restrict the direct public route for private uploads.
- Serve private images only through an authenticated, authorized handler or short-lived signed URLs.
- Verify that a student cannot read another student's image and an unauthenticated user cannot read private answer images.
- Add regression tests for anonymous access, cross-student access, valid owner access, and invalid/missing files.
- Consider whether filenames are predictable and whether upload metadata or logs leak them.

Treat this as a release blocker until resolved and tested.

### Migration/taxonomy risk to reconcile

Migration 005 creates a canonical concept ID by slugging `official_chapter_name` and upserts using a `subject_id`. If different subjects contain the same chapter name, they may share an ID and later update the subject association unexpectedly.

**Required follow-up:**
- Inspect the actual taxonomy for duplicate chapter names across boards, classes, and subjects.
- Decide whether concept identity is subject-scoped or deliberately shared across subjects.
- If subject-scoped, include stable subject/board/class identity in the canonical ID or use a proper composite key.
- Add a regression test for duplicate chapter names across distinct subjects.
- Check existing data before changing identifiers; do not silently orphan question links.

### Report correctness and quality tests still needed

Add or verify representative tests for:
- A question carrying multiple error codes.
- The same error recurring across multiple tests.
- Chapters with very little evidence or no attempts.
- A student with no attempted questions.
- Chapter and error ranking ties.
- Empty evaluations and partial evaluation.
- Recommendation selection when evidence is weak.
- PDF pagination, long comments, and maximum-size report output.
- Consistency between stored marks, score/percentage, attempt rate, accuracy, chapter performance, and error distribution.

The student/guardian report should clearly explain why marks were lost and what to practise next. It must not overstate conclusions from very little evidence.

### Production gate before merge/deploy

- Inspect live Aiven schema and migration state read-only.
- Review migrations 005 and 006 and their ordering/dependencies.
- Confirm backup and restore procedure, including a tested restore path if feasible.
- Confirm deployment environment variables, storage configuration, and whether Render auto-deploy is enabled.
- Run the read-only audit first; do not apply production migrations until the proposed changes and output are reviewed and explicitly approved.
- Verify rollback/forward-recovery options before any schema change.

---

## 3. PR #28 — `audit-curriculum-migration`

**Status at audit:** Open PR. Head commit `3f0c6bb9a5dc4aae83b43c5d4b3709bcc13cde53`. CI run `36550882688` passed.

PR #28 overlaps with migration 005/audit work in PR #31. **Do not merge both PRs wholesale** before reconciling their common files and responsibilities.

### Finding A — expected enrollment insert count is overstated

In `question_bank/migrations/005_curriculum_question_reuse_audit.py`, `expected_enrollment_inserts` was set equal to eligible registrations. That overstates new insertions if some eligible registrations already have the relevant enrollment.

**Fix:** calculate the number of eligible registrations that do *not* already have the matching enrollment, using a `LEFT JOIN ... IS NULL` or `NOT EXISTS` query with the correct identity columns. Report eligible registrations, existing enrollments, and genuinely new insertions as separate values.

### Finding B — subject-name dictionary collisions

The audit maps subject name to subject ID. Repeated names (for example, Computer Applications used by different board/class/subject definitions) can collide and overwrite one another.

**Fix:** use a stable canonical subject identity or composite key that includes the relevant board, class, subject code, and/or canonical subject identity. Add tests with repeated display names for distinct subjects.

### Finding C — read-only behavior needs proof

A green CI run does not establish that the audit ran against the live Aiven database, nor that it is strictly read-only in all code paths.

**Required follow-up:**
- Review every database operation and connection mode used by the audit.
- Ensure it does not create, update, delete, migrate, or otherwise mutate live data.
- Test against a disposable database with representative existing/missing enrollments and duplicate subject names.
- Record the exact command, database target identity (without credentials), output, and timestamp when running the live read-only audit.
- Keep secrets out of logs, commits, and the audit report.

### Reconciliation decision

Consolidate useful audit and migration work into one release path, likely PR #31 if that remains the V1 release branch. Compare all overlapping migration, audit, schema-guard, and test files before porting changes. Fix the issues above and retest.

Only after all useful PR #28 work is included elsewhere should PR #28 be closed as superseded. Do not close it before the reconciliation is complete.

---

## 4. PR #32 — `docs/groq-question-ingestion-workflow`

**Status at audit:** Open PR. Head commit `34a5554c57e8c90dac0bce97e5505ce0cb0eb285`. CI run `39916653086` passed.

### What is good about the current prototype

- It is a local/prototype workflow rather than an automatic production publisher.
- It does not directly write to the production database or publish extracted questions automatically.
- It preserves a human-review boundary.
- It uses a provider wrapper and has page limits/provenance concepts.
- The current tests use mocked behavior and passed CI.

### What remains unproven

1. No verified live Groq API request/model-access test was demonstrated in the audit.
2. No representative Maths PDF benchmark against manually verified expected questions was completed.
3. `AIJSONBulkImporter` is initialized with an empty existing-question collection, so its duplicate statistics do not prove uniqueness against the real question bank.
4. Mocked tests do not validate real extraction quality, provider output variation, rate limits, or failures.

### Required benchmark before merging/depending on it

Build a small, permitted sample set of representative CBSE/ICSE Mathematics PDFs and manually prepare a gold/reference set. Include, where available:
- Printed and scanned pages.
- Fractions, exponents, roots, matrices, and other mathematical notation.
- Multi-part questions and subquestions.
- MCQ options and answer choices.
- Marks and section instructions.
- Diagrams/graphs/geometry figures.
- Questions spanning page breaks.
- Headers/footers/page numbering that could be mistaken for question content.

Record:
- Exact source document/page provenance.
- Number of expected questions versus extracted questions.
- Missing, duplicated, malformed, or invented content.
- Accuracy of question text, options, marks, and subpart structure.
- Failure/timeout behavior.
- Human correction time per page/question.
- Estimated cost/latency under the actual provider/model plan in use.
- Duplicate comparison against existing canonical question-bank data.

Keep human review before acceptance. No automatic publishing or production DB writes until quality, deduplication, and recovery behavior are demonstrated. The commercial question is whether extraction saves enough human time to justify its cost—not whether an API call technically works.

---

## 5. Other open/stacked pull requests

The audit snapshot identified these open PRs:
- **#4:** URL ingestion, branch `stage-3a-url-ingestion`; reported non-mergeable at audit time.
- **#5:** Shaalaa parser, branch `stage-3b-shaalaa-parser`; stacked on #4.
- **#6:** MarkItDown PDF extraction, branch `feature/markitdown-pdf-extraction`; reported non-mergeable and its branch is an ancestor of the merged question-extraction implementation.
- **#9:** cloud-to-local question-bank sync, branch `cloud-to-local-question-sync`, based on `question-bank-dual-sync`.
- **#24:** JSON error-guidance v2, branch `fix-json-error-guidance-v2`.
- **#28:** migration audit.
- **#31:** V1 performance/release hardening.
- **#32:** Groq PDF question ingestion.

### PR #4 and #5: resolve as a stack

- #5 is based on `stage-3a-url-ingestion`; it should not be merged directly into master as though it were independent.
- Resolve/rebase and validate #4 first, or explicitly decide that URL ingestion is being abandoned.
- Then rebase/review #5 against the intended base and validate it independently.
- Avoid merging an old base simply to make the stacked PR appear mergeable.

### PR #6: likely superseded

`feature/markitdown-pdf-extraction` was reported as an ancestor of the merged `feature/question-extraction` branch / PR #8. Verify that the desired implementation and tests are retained in the merged code. If confirmed, close PR #6 as superseded and then delete its branch if no unique work remains.

### PR #9 and sync architecture

`cloud-to-local-question-sync` uses `question-bank-dual-sync` as its base and was reported to contain 10 unique commits relative to master; `question-bank-dual-sync` had seven unique commits relative to master. The merged implementation uses `exam_platform/question_sync.py`, while the sync branch introduces a parallel `exam_platform/question_bank_sync.py` design.

Do not maintain two overlapping sync implementations without a clear requirement. Decide whether cloud-to-local sync is genuinely needed for the MVP, identify the system of record and conflict rules, and choose one architecture. Keep both branches until that decision and any useful changes are reconciled.

### PR #24

Keep `fix-json-error-guidance-v2` pending. Review it after release blockers and migration reconciliation; test the guidance with real malformed/edge-case question JSON and ensure errors are actionable without silently changing question meaning.

---

## 6. Branch inventory and cleanup recommendations

The audit found 33 branch names:

1. `audit-curriculum-migration`
2. `cloud-to-local-question-sync`
3. `curriculum-multi-board-question-reuse`
4. `docs/expanded-school-subject-scope`
5. `docs/extraction-audit-status`
6. `docs/groq-question-ingestion-workflow`
7. `docs/notebooklm-workflow`
8. `docs/production-registration-architecture`
9. `dual-db-sync`
10. `feature/markitdown-pdf-extraction`
11. `feature/question-extraction`
12. `feature/v1-performance-report`
13. `fix-json-error-guidance`
14. `fix-json-error-guidance-v2`
15. `fix-review-app-persistent-helper-order`
16. `fix-review-app-remaining-syntax`
17. `fix-review-app-syntax`
18. `improve-sequential-extraction-review`
19. `master`
20. `question-bank-dual-sync`
21. `schema-v2-canonical-question-ingestion`
22. `stage-1-question-ingestion`
23. `stage-2-pdf-ingestion`
24. `stage-3a-url-ingestion`
25. `stage-3b-shaalaa-parser`
26. `stage-4-taxonomy-applied-math`
27. `stage-5-registration-eligibility`
28. `stage-6-google-registration-pipeline`
29. `stage-7-google-form-webhook`
30. `stage-7-google-registration-webhook-v2`
31. `stage-8-extraction-hardening`
32. `stage-8-json-contract`
33. `v1.3-canonical-question-bank`

### 6A. Shortlist: 21 branches recommended for deletion after final safety checks

**Merged-PR branches whose branch heads matched the exact merged PR head at the time of audit:**
- `curriculum-multi-board-question-reuse` — PR #27 merged.
- `stage-4-taxonomy-applied-math` — PR #13 merged.
- `stage-5-registration-eligibility` — PR #14 merged.
- `stage-6-google-registration-pipeline` — PR #15 merged.
- `docs/expanded-school-subject-scope` — PR #26 merged.
- `docs/extraction-audit-status` — PR #21 merged.
- `docs/production-registration-architecture` — PR #12 merged.
- `dual-db-sync` — PR #11 merged.
- `feature/question-extraction` — PR #8 merged.
- `schema-v2-canonical-question-ingestion` — PR #10 merged.
- `fix-review-app-syntax` — PR #17 merged.
- `fix-review-app-remaining-syntax` — PR #18 merged.
- `fix-review-app-persistent-helper-order` — PR #19 merged.
- `stage-7-google-registration-webhook-v2` — PR #20 merged.
- `stage-8-extraction-hardening` — PR #22 merged.
- `stage-8-json-contract` — PR #23 merged.
- `improve-sequential-extraction-review` — PR #25 merged.

**Branches reported as having zero unique commits relative to master:**
- `fix-json-error-guidance` — 0 ahead, 5 behind.
- `stage-1-question-ingestion` — 0 ahead, 56 behind.
- `stage-2-pdf-ingestion` — 0 ahead, 43 behind.
- `v1.3-canonical-question-bank` — 0 ahead, 177 behind.

Before deleting any of these, verify the current branch heads and open PR/base-branch references again. Confirm branch protection does not block deletion and that no unmerged useful commit, release tag, deployment, or active work depends on the branch. A branch being behind is not, by itself, enough evidence to delete it.

### 6B. Conditional cleanup

- **`feature/markitdown-pdf-extraction`:** verify desired work is retained by merged PR #8, close PR #6 as superseded if confirmed, then delete.
- **`stage-7-google-form-webhook`:** PR #16 was closed unmerged and an updated v2 exists in merged PR #20. Verify the v2 implementation retains required behavior, then delete.
- **`docs/notebooklm-workflow`:** do **not** delete until useful documents are preserved. It was reported six commits ahead and 118 behind master. Its useful files include `NOTEBOOKLM_WORKFLOW.md`, `AUTOMATION_WORKFLOW.md`, and `PRODUCT_STRATEGY.md`. Port the relevant docs into a small PR or archive them first; do not merge the entire stale branch.

### 6C. Keep for now

- `master` — primary branch.
- `feature/v1-performance-report` — PR #31; fix blockers and reconcile migrations.
- `audit-curriculum-migration` — PR #28; reconcile with #31.
- `docs/groq-question-ingestion-workflow` — PR #32; benchmark first.
- `fix-json-error-guidance-v2` — PR #24; pending review.
- `stage-3a-url-ingestion` — PR #4; resolve base/mergeability.
- `stage-3b-shaalaa-parser` — PR #5; stacked on #4.
- `cloud-to-local-question-sync` — PR #9; pending architecture decision.
- `question-bank-dual-sync` — base for PR #9; keep until sync decision.

After the safe branches are cleaned up and open work is reconciled, the target is roughly nine core branches including master and active work branches. The target is not a reason to delete a branch prematurely.

**No branches were deleted during this audit.** All deletion items above are recommendations only.

---

## 7. CI evidence and limits

### PR #31
- Head: `97c1423b8f9bcf23febb01b9d016e9db73fe2f3c`
- Workflow run: `39837105036`
- Reported passed.
- Included isolated MySQL, migrations 005/006, app startup, `test_exam_platform.py` smoke test, and the remaining tests.

### PR #32
- Head: `34a5554c57e8c90dac0bce97e5505ce0cb0eb285`
- Workflow run: `39916653086`
- Reported passed.
- Tests were mocked; this does **not** prove real Groq API access or extraction quality.

### PR #28
- Head: `3f0c6bb9a5dc4aae83b43c5d4b3709bcc13cde53`
- Workflow run: `36550882688`
- Reported passed.
- Does **not** prove a production Aiven read-only audit was executed successfully.

### Master workflow concern

The master `.github/workflows/tests.yml` was reported to run `pytest -q --ignore=test_exam_platform.py`. PR #31's isolated MySQL smoke coverage is stronger for the exam platform. A combined master status check returned no status entries; that was not evidence of failure. Recheck current workflows and status before any release decision.

---

## 8. Product and business constraints — keep these in view

Improvia is intended to become a **Mathematics Assessment & Improvement System**, not merely a test-series seller.

### Initial customer and scope
- Begin with CBSE/ICSE Class 10–12 Mathematics.
- Do not launch Class 6–9, multiple subjects, JEE, state boards, live teaching, or a broad EdTech product as part of the initial commercial pilot.
- Focus on students who study but still lose marks, students who want strict evaluation, and parents who need visible progress/accountability.
- The average/struggling student who cannot explain why marks are lost may have more urgent need than the already high-scoring student.

### Core workflow
**Test → submission → evaluation → error diagnosis → analytics → personalised feedback → progress tracking → next test → updated profile.**

Manual marking is appropriate for the MVP. AI should not be the initial authority for grading handwritten Mathematics. Later, AI may assist with extraction, preliminary evaluation, uncertainty detection, question selection, and reports—but keep human verification where marks are affected.

### Error taxonomy in use
- C01 — Calculation
- C02 — Conceptual
- C03 — Formula
- C04 — Sign
- C05 — Incomplete steps
- C06 — Wrong method
- C07 — Missing justification
- C08 — Misunderstood question
- C09 — Time/attempt issue

Preserve error codes as structured data so the taxonomy can evolve without rewriting historical records.

### Commercial validation
The first meaningful milestone is **20–30 real paying students**, not an app, an AI grader, 1,000 registrations, or a revenue target. Validate:
- Registration → payment conversion.
- Payment → test attempt.
- Attempt → report viewed.
- Test 1 → Test 2 → Test 3 continuation.
- Retention and referrals.
- Student/parent satisfaction and willingness to pay.
- Evaluation time and cost per student.
- Whether reports actually change what students practise next.

Possible early price hypotheses discussed: a ₹49–₹99 diagnostic trial, approximately ₹299–₹499/month, and an intensive ₹699–₹999/month offer. These are hypotheses to test, not validated market prices. Do not assume weekly repeat usage, parent trust, automatic sales, or profit from revenue alone.

### Technology principle
Use low-cost infrastructure and keep the workflow understandable: Forms/Sheets → Python/pandas → charts and report PDF → WhatsApp/email. Automate only after the manual process demonstrates that customers value the diagnosis. Do not build complex infrastructure because it is technically interesting.

---

## 9. Recommended execution order for the next work session

### Phase 1 — release blockers
1. Open PR #31 and re-check current head/base/status.
2. Trace answer-image upload and retrieval; connect the intended persistent storage abstraction.
3. Remove/restrict public direct upload serving.
4. Add and run privacy/ownership/storage regression tests.
5. Add report metric and PDF edge-case tests.

### Phase 2 — migration reconciliation
6. Diff PR #28 against PR #31 for every overlapping migration, audit, schema guard, and test.
7. Fix `expected_enrollment_inserts` so existing enrollments are not counted as new inserts.
8. Fix subject identity collisions.
9. Resolve canonical concept-ID collisions across subjects.
10. Run tests against a disposable database and inspect migration ordering.
11. Run the production audit in read-only mode against Aiven and review its output. Do not apply migrations until explicitly approved.

### Phase 3 — ingestion and sync decisions
12. Build and run the real-PDF Groq benchmark with a manually verified gold set.
13. Keep human review; do not auto-publish extracted questions.
14. Decide whether cloud-to-local question-bank sync is needed and choose one sync architecture.
15. Resolve PR #4/#5 as a stack; decide whether PR #6 is superseded by PR #8.
16. Review PR #24 after higher-risk issues.

### Phase 4 — branch hygiene
17. Recheck current refs and open PR/base dependencies.
18. Preserve/port the three useful NotebookLM/workflow/strategy docs.
19. Close superseded PRs only after verifying their useful work is retained.
20. Delete the 21-branch shortlist only after the safety checks; then handle conditional branches.
21. Recheck CI and branch list after cleanup.

### Phase 5 — MVP readiness
22. Keep commercial pilot scope at CBSE/ICSE Class 10–12 Maths.
23. Test the end-to-end student/guardian experience with real sample reports.
24. Measure whether students understand the diagnosis and know what to do next.
25. Validate willingness to pay and repeat use before expanding the platform.

---

## 10. Resume checklist

At the beginning of the next session:
- [ ] Read this document first.
- [ ] Re-check live PR state, branch heads, CI and base branches; the audit snapshot may have changed.
- [ ] Start with PR #31's image storage and public-upload access issues.
- [ ] Do not delete branches, merge PRs, or apply production migrations without a fresh check.
- [ ] Keep secrets and student personal data out of logs, sample fixtures, and committed reports.
- [ ] Make small, tested changes and record the resulting commit/PR.
- [ ] Keep the business goal visible: explain avoidable lost marks and show improvement—not merely deliver another test.

**Audit conclusion:** The repository has substantial groundwork, but passing CI and the presence of features do not establish production readiness or commercial demand. Prioritise privacy, durable student submissions, migration safety, evidence-based question ingestion, and real-user validation before beautification or platform expansion.
