> **Archive note:** Historical audit snapshot from docs/ai-development-guidelines, based on master commit 1038a2cb (15 November 2026). The 17 November audit is the newer repository review. Do not treat estimates or branch-relative findings as current without revalidation.

# Improvia — Full Development, Security & Commercial Readiness Audit

**Audit date:** 15 November 2026  
**Repository:** Megha-2-Paul/edtech-mathematics-assessment  
**Audit baseline:** master at 1038a2cb9540b953a2a84452fba90dcd771ffe7d  
**Technology:** Python, Flask, Jinja2, SQLAlchemy, MySQL  
**Document type:** Read-only repository audit and delivery estimate  
**Status:** Findings and estimates; not a security certification, production sign-off, or implementation approval

---

## 1. Executive summary

Improvia is more advanced than a basic mock-test prototype. The repository contains a substantial Flask application, question-bank and curriculum work, student exam routes, teacher/admin workflows, manual evaluation, error diagnosis, reporting foundations, database models and migration work.

However, the existence of code, tests, documentation or a pull request is not proof that a feature is complete, integrated on master, safe with real student data, or working in production.

**Overall conclusion:** Improvia is in the pre-launch engineering and release-readiness stage. It has a meaningful functional foundation, but the complete student-to-report-to-improvement loop has not been demonstrated by this audit in a production-like environment. Security, persistence, migration, workflow integration and report correctness must be verified before real student use.

### 1.1 Indicative maturity assessment

These percentages are subjective engineering judgements based on the inspected repository snapshot. They are not test coverage, code-completion measurements, or independently verified production-readiness scores.

| Dimension | Indicative assessment | Interpretation |
|---|---:|---|
| Functional foundation | ~70% | Many core building blocks exist |
| Founder-operated MVP readiness | ~50% | Integration and release evidence remain incomplete |
| Commercial readiness | ~30% | Operational, security and production proof is incomplete |

Do not use these percentages as a public product claim or as a substitute for the acceptance criteria in this document.

### 1.2 Time estimate

| Workstream | Estimated focused engineering effort |
|---|---:|
| Phase 0 — Security and release hardening | 20–30 hours |
| Phase 1 — Complete student assessment loop | 20–30 hours |
| Phase 2 — Diagnosis and reporting correctness | 15–25 hours |
| Phase 3 — End-to-end testing and deployment | 15–25 hours |
| **Total estimated engineering effort** | **70–110 hours** |
| Supervised pilot after release gates | Additional 2–4 weeks |

At approximately 8–12 focused engineering hours per week, the working estimate is **8–12 weeks** for a founder-operated MVP, assuming timely local testing and no major unexpected migration or deployment blockers. The arithmetic range can extend beyond this if available weekly time is lower or defects require rework.

A more complete commercial SaaS offering may require another 2–4 months after the MVP, depending on customer evidence and the features actually approved. This is not a commitment or guaranteed delivery date.

---

## 2. Audit scope, method and evidence limits

### 2.1 What was inspected

The audit used GitHub's remote repository as its source of truth for the inspected commit and included:

- Repository development instructions and project documentation.
- master branch identity and recent repository state.
- Branch inventory and selected branch comparisons.
- Open pull-request inventory and selected PR file lists/descriptions.
- Selected application, evaluation, diagnosis, media, configuration, migration and test files.
- Existing commercial platform roadmap and product workflow documentation.

Files and areas inspected included:

- README.md
- AGENTS.md
- PROMPTS.md (repository development prompt guidance)
- docs/CHATGPT_INSTRUCTIONS.md
- docs/IMPROVIA_COMMERCIAL_PLATFORM_ROADMAP.md
- docs/FEB_2027_TUITION_IMPROVIA_LAUNCH_PLAN.md
- PRODUCT_WORKFLOW.md
- PRODUCTION_ARCHITECTURE.md
- exam_platform/app.py
- exam_platform/admin.py
- exam_platform/evaluation.py
- exam_platform/diagnosis.py
- exam_platform/reporting.py
- exam_platform/media.py
- exam_platform/mock_data.py
- exam_platform/student_csrf.py
- exam_platform/teacher_csrf.py
- wsgi.py
- question_bank/migrations/005_curriculum_question_reuse.py
- selected tests including test_answer_image_security_contract.py and test_diagnosis_evaluation_completion.py

The inspection was targeted, not a line-by-line review of every file in the repository. The list above records representative inspected sources, not an assertion that every route, model, template or migration was exhaustively reviewed.

### 2.2 What was not done

The following were not performed as part of this remote audit:

- No local working tree or uncommitted changes were inspected.
- No Python test suite was executed.
- No application was started locally.
- No MySQL integration test was run by the auditor.
- No Aiven database was accessed.
- No production Render settings or live deployment were inspected.
- No Cloudinary account, asset privacy mode or storage durability was verified.
- No backup or restore was performed.
- No real student data was accessed.
- No migration was executed.
- No branch was merged, deleted, rebased or force-pushed.

Therefore, this report must not claim that tests passed, production is secure, the database is current, or deployment is working.

### 2.3 Evidence labels used in this report

- **Observed in source:** present in the inspected code snapshot.
- **Documented:** described in repository documentation, but not thereby proven implemented.
- **PR-only / branch-only:** described or present in a non-master branch or pull request; not assumed to be on master.
- **Needs verification:** code or configuration requires broader inspection or runtime evidence.
- **Not verified:** no live or execution evidence was collected.
- **Recommendation:** proposed future work, not an existing defect unless stated as observed.

---

## 3. Product goal and approved MVP boundary

Improvia is intended to show students:

1. Where they lose marks.
2. Why they lose marks.
3. What they should practise next.
4. Whether they improve on a later assessment.

The core product loop is:

~~~text
Registration
  -> Eligibility
  -> Assessment
  -> Answer persistence
  -> Submission
  -> Evaluation
  -> Error diagnosis
  -> Report
  -> Recommended practice
  -> Next assessment
  -> Progress comparison
~~~

This is a diagnostic assessment and improvement system, not merely a mock-test website.

### 3.1 Current documented scope

The current README describes Mathematics for Classes 9–12, CBSE and ICSE where curriculum and question-bank content are validated. It also identifies Class 10 CBSE Information Technology (Code 402) and Computer Applications (Code 165) as separate computer-related subjects. The commercial roadmap describes its initial primary market as CBSE/ICSE Mathematics, initially Classes 10–12.

**Documentation discrepancy to reconcile:** README scope says Mathematics Classes 9–12, while the commercial roadmap's opening summary says Classes 10–12. Confirm the intended approved pilot classes and update documentation consistently before advertising or publishing eligibility.

Technical support for a subject or class does not automatically approve it for launch. Preserve distinct subject identities, including CBSE IT 402 and Computer Applications 165.

### 3.2 Product principles

- Keep the first release focused on reliable assessment, human-confirmed marking, explainable diagnosis and improvement measurement.
- Handwritten Mathematics evaluation remains human-controlled.
- Do not introduce unsupervised AI grading.
- A blank answer alone does not establish a conceptual weakness.
- Preserve the existing C01–C09 error taxonomy unless a separately reviewed change is justified.
- Avoid building dashboards, payments, multi-tenancy, mobile applications or AI features before the core workflow is reliable and the pilot provides evidence.

---

## 4. Current feature-by-feature development assessment

The statuses below are repository-level assessments, not production certification.

| Component | Current assessment | Remaining work |
|---|---|---|
| Flask application foundation | Substantial implementation | Full integration and production review |
| Student registration | Foundation exists | Verify approval, identity reuse, activation and idempotency |
| Eligibility and curriculum | Substantial implementation | Validate real enrollment and all board/class/subject cases |
| Question bank | Substantial implementation | Content quality, provenance and publishing controls |
| PDF/JSON ingestion | Foundation exists | Benchmark extraction; keep human review |
| Student authentication | Incomplete on master relative to PR work | Reconcile PR #31/#35 and prove runtime access controls |
| Exam interface | Substantial implementation | End-to-end persistence and mobile checks |
| Timer and attempt lifecycle | Implemented foundation | Verify server authority, expiry, resume and concurrency |
| Handwritten uploads | Implemented foundation | Verify private durable storage, validation and access isolation |
| Teacher/admin interface | Implemented foundation | Verify authentication, permissions, CSRF and workflow |
| Manual marking | Implemented foundation | Verify partial evaluation, revisions, audit and transaction integrity |
| C01–C09 diagnosis | Implemented foundation | Validate interpretation and calculation correctness |
| HTML reporting | Implemented foundation | Validate report accuracy, ownership and completeness |
| PDF report delivery | Not confirmed on master by inspected evidence | Reconcile PR #31 and verify secure generation/delivery |
| Student history | Foundation exists | Validate history calculations and reassessment comparison |
| Personalised practice | Basic rule-based foundation | Validate recommendations against evidence and available content |
| CI and integration tests | Partial / not established by this audit | Run and repair full MySQL-backed suite |
| Production deployment | Configuration documented | Verify live settings and deployment behaviour |
| Commercial operations | Primarily planned | Privacy, support, retention, backups, incident response and customer validation |

### 4.1 Question bank and curriculum

Observed/documented foundations include:

- Canonical curriculum structures and subject identity.
- Board, class and subject-specific curriculum mapping.
- Separation of Mathematics and Applied Mathematics.
- Question-bank ingestion and validation workflows.
- Structured JSON ingestion and PDF extraction foundations.
- Source/provenance and human-review concepts.
- Curriculum/question-reuse migration work.

This is meaningful groundwork. The immediate priority should not be another extraction provider. Prioritise validated questions, correct official chapter names, provenance, human approval and release stability.

### 4.2 Assessment engine

The inspected application contains routes and logic for:

- Test access and attempts.
- Answer saving.
- Handwritten image upload and deletion.
- Submission preview.
- Submission confirmation.
- Attempt access checks.
- Private answer-image proxy handling.

The current submission implementation checks required handwritten uploads and updates the attempt's submitted status and timestamp. The inspected code also has an access helper and a test contract asserting that submitted attempts reject mutation methods.

Remaining verification includes:

- Atomic creation/persistence of response rows for every question, including unanswered questions.
- Server-authoritative deadline enforcement.
- Resume after refresh/reconnection without resetting time.
- Duplicate submission and concurrent request behaviour.
- Upload failure and retry behaviour.
- Correct attempt-state transitions.
- Durable storage independent of an ephemeral application filesystem.

PR #31 describes a more complete implementation for immutable submissions and atomic materialisation of unanswered response rows. Do not assume that work is on master until code is reconciled.

### 4.3 Teacher evaluation

Observed foundations in exam_platform/evaluation.py include:

- Teacher submission listing and question-wise evaluation.
- Marks validation against the question's maximum.
- Finite numeric checks and 0.5 mark increments.
- MCQ scoring.
- Error-code selection and evaluator comments.
- Evaluation error persistence.
- Attempt score/percentage/attempt-rate calculation.
- Question-history updates.

Remaining work:

- Prove all evaluation routes require an authenticated, authorised teacher in every deployment mode.
- Verify that a teacher can access only assigned/authorised student submissions.
- Verify evaluation saves are transactional across response marks, errors, attempt totals and history.
- Test partial evaluations and safe re-evaluation.
- Record an audit trail for every mark/comment/error-code change.
- Test multiple error codes, partial marks and no-attempt cases.
- Verify a report cannot be treated as final until all required questions are evaluated.

The inspected teacher evaluation rendering references an uploaded_file endpoint for answer images, and register_evaluation contains a send_from_directory wrapper. The complete route registration and exposure path must be traced before release. This is a verification item, not a confirmed exploitable public route based on the limited search performed.

### 4.4 Diagnosis and reporting

Observed foundations include C01–C09, diagnosis helpers, report-building logic and student result/report routes.

Specific correctness concerns identified during source inspection:

1. The inspected diagnosis accuracy calculation uses fully correct questions divided by attempted questions. This may not represent marks-based accuracy where subjective answers receive partial marks. Define the product metric explicitly and test it against hand-calculated examples.
2. Recurring-error logic needs to prove that the same error occurred across distinct assessments, rather than merely relying on an aggregate count. Verify distinct-attempt semantics and the minimum evidence threshold.
3. Chapter/topic analysis and marks-lost totals must reconcile with response-level marks and evaluation-error rows.
4. An unanswered question must not automatically become a conceptual weakness.
5. PDF report generation/delivery was not confirmed on the inspected master source. PR #31 describes a two-page PDF implementation; reconcile it before deciding what remains.

A trustworthy report should explain the student's score, where marks were lost, the evidence-backed reasons, chapter/topic performance, strengths, weaknesses, repeated mistakes, next practice and comparable progress over time.

---

## 5. Security and release-readiness audit

The project roadmap already contains a substantial security/privacy requirements catalogue. That document is a requirements and acceptance-criteria document, not evidence that the controls are implemented or live.

The following is the prioritised verification backlog.

### 5.1 Identity and authentication

- Reconcile student login, activation, password hashing, token expiry and lockout work from PR #31 and #35.
- Confirm no real student can create or use a guest identity.
- Confirm activation tokens are random, single-use, time-limited and stored hashed.
- Confirm older activation links are invalidated when a new one is issued.
- Confirm session clearing/rotation on login, logout and privilege change.
- Confirm safe lockout reset and account recovery.
- Verify guardian-assisted recovery where relevant for minors.
- Configure privileged staff access securely; consider MFA for production teacher/admin accounts.

The inspected wsgi.py uses HTTP Basic Authentication for /teacher paths when a teacher password is configured. In Render mode it returns 503 if the password is missing; outside Render, the access gate can be bypassed when no password is configured. The username has a fallback value of teacher. Verify the actual production environment and do not rely on a development fallback. Determine whether the intended final teacher authentication should remain Basic Auth or move to the application account model.

### 5.2 Authorisation and student ownership

For every route, API, export, download, report and storage operation, verify:

- Anonymous requester is denied.
- Owning student is allowed only for their own records.
- Another student is denied.
- Authorised teacher is allowed within their assigned scope.
- Unauthorised teacher is denied.
- Admin actions are limited and auditable.

Never rely on unguessable IDs, hidden buttons or frontend-only checks as authorisation.

### 5.3 CSRF and web security

Student and teacher CSRF modules exist in the inspected repository. The student module names mutation endpoints including starting a test, saving a response, uploading/deleting an image and submitting an attempt. The teacher module applies checks to teacher paths and extraction-review endpoints.

Remaining verification:

- Confirm both protections are registered in every application entry point.
- Confirm all state-changing routes are covered, including routes outside /teacher.
- Confirm every corresponding form and JavaScript request sends the expected token.
- Test missing, invalid and valid CSRF tokens.
- Review secure cookie flags, HTTPS, SameSite behaviour, security headers, CSP compatibility, origin/redirect validation and rate limiting.
- Test request body limits and upload processing limits.

### 5.4 Handwritten answer and report storage

- Verify uploaded answer images and reports are stored durably in private storage.
- Verify Cloudinary or any configured provider uses authenticated/private assets, not public delivery.
- Verify no raw public upload path can bypass ownership checks.
- Use authenticated proxy delivery or short-lived signed URLs after authorisation.
- Validate extension, detected MIME type, file signature, size, dimensions and image decoding.
- Generate random storage keys; do not trust user-controlled paths.
- Test path traversal, invalid file, oversized file, missing file, upload retry, delete and cross-student access.
- Inventory and remediate any legacy public assets.
- Define retention/deletion for originals, thumbnails, reports and backups.
- Verify storage durability across application restarts/redeployments.

The inspected app.py contains an authenticated answer-image proxy and security headers; the selected test contract checks private/no-store caching and nosniff. These are positive code-level foundations, but do not prove the provider configuration, every access path or all real deployment behaviour.

### 5.5 Timer, submission and attempt integrity

- Server is authoritative for start time, deadline, expiry and attempt status.
- Browser countdown is display-only.
- Refresh resumes the same attempt and remaining server-computed time.
- Expiry is enforced server-side even if the browser remains open.
- Submission is atomic and idempotent.
- Repeated submit attempts cannot create duplicate results.
- Submitted attempts are immutable except through a separately authorised and audited correction process.
- All required response rows exist, including unanswered questions.
- Concurrent saves/submission are handled safely.
- Partial upload or database failure leaves the attempt in a consistent recoverable state.

### 5.6 Secrets and configuration

- No secrets, database URLs, passwords, API keys, webhook secrets or tokens in Git.
- Production fails safely when required configuration is missing.
- No development fallback secrets or default privileged credentials.
- Separate local, CI, staging and production credentials.
- Rotate credentials if exposure is suspected.
- Verify actual Render, Aiven and Cloudinary settings without copying secrets into audit output.

### 5.7 Privacy, minors and legal readiness

Before real student data is used:

- Publish a clear privacy notice and terms.
- Define purpose, collection, access, sharing, retention and deletion.
- Obtain appropriate guardian consent/verification where legally required.
- Separate optional marketing consent from assessment processing.
- Document processors, subprocessors, storage location and third-party terms.
- Do not send real student work or personal data to AI providers without explicit approval, appropriate consent and privacy review.
- Define data access, correction, withdrawal, deletion and grievance procedures.
- Define incident response and breach notification responsibilities.
- Obtain qualified India-specific legal/accounting advice on applicable DPDP requirements, consumer terms, payments, tax and invoicing.

This is a launch-readiness checklist, not legal advice or a finding that every listed law applies to every workflow.

---

## 6. Database, migration and deployment readiness

### 6.1 Database source of truth

Repository documentation describes:

- Render as the Flask application host.
- Aiven MySQL as the production database.
- Local MySQL as the development/test database.
- Cloudinary as the documented image storage provider.
- QUESTION_BANK_SYNC_DATABASE_URL as an optional question-bank sync connection, not general student-data replication.

These are documented architecture choices. Actual live configuration was not verified.

Never assume local MySQL and Aiven are synchronised. Never run an unapproved production migration or destructive write.

### 6.2 Migration reconciliation

Important migration-related work includes:

- Migration 005 for curriculum/question reuse.
- A read-only migration audit script and related PR work.
- Migration 006 student-access work described by PR #31.
- Migration 006 exam-monitoring-mode work present in the current master history.

Migration numbering and file names must be checked against actual master and production schema history before proposing any new migration. Do not assume that the same migration number on different branches refers to the same schema change.

Before any production migration:

1. Inspect the actual Aiven schema and migration history read-only.
2. Confirm exact dependency/order and whether the migration has already been applied.
3. Run the audit against an isolated local/disposable MySQL database.
4. Verify idempotency and rollback/restore steps.
5. Obtain a verified backup and restore path.
6. Obtain explicit approval.
7. The repository owner executes production migration separately.

### 6.3 Deployment and operations

Verify:

- Production environment variables and secret configuration.
- Render service start command and deployment behaviour.
- Whether merge/push triggers automatic deployment.
- Aiven connectivity and schema compatibility.
- Cloudinary authenticated/private asset delivery.
- Health checks and error monitoring.
- Database backup schedule and successful restore evidence.
- Deployment rollback procedure.
- Incident response and support contact.
- Rate limiting, logging and alerting.
- Privacy notice, retention and deletion processes.

A successful CI run does not prove live Render, Aiven or Cloudinary configuration.

---

## 7. GitHub branches and pull-request reconciliation

### 7.1 Repository snapshot

At the time of inspection, GitHub returned 28 branches. The branch inventory included master, multiple documentation branches, curriculum/migration branches, registration branches, extraction branches and security/feature branches.

Current master audit baseline:

~~~text
1038a2cb9540b953a2a84452fba90dcd771ffe7d
~~~

The branch list and PR states can change after the audit date. Re-check before any implementation or merge decision.

### 7.2 Relevant pull requests and branches

| PR | Subject | Audit observation | Recommendation |
|---|---|---|---|
| #31 | Harden Improvia V1 end-to-end platform | Large coordinated implementation described for authentication, immutable submissions, private images, reports, migrations and MySQL CI | Do not merge blindly; reconcile code and migration dependencies |
| #35 | Student authentication and access migration security | Additional authentication, lockout, teacher-link and migration-audit tests | Review overlap/dependencies with #31 |
| #28 | Aiven/curriculum migration audit | Migration 005 audit and migration changes | Compare against master and production history before any migration |
| #32 | Local-only Groq PDF extraction prototype | Experimental extraction path, not core release work | Defer until release blockers are resolved |
| #24 | Malformed AI JSON upload errors | Ingestion usability improvement | Lower priority than platform security and end-to-end workflow |
| #37 | Admin question workflow | Changed exam_platform/admin.py and tests/test_admin_questions.py | Verify current disposition and unique value before acting |
| #36 | Development guidance and prompt library | Documentation branch; not listed among the open PRs returned during this audit | No action required for this audit |

The open PR search at audit time returned #24, #31, #32 and #35. This is a point-in-time observation, not a permanent PR status.

### 7.3 Branch divergence evidence

Selected GitHub compare results against master:

| Branch | Ahead | Behind | Implication |
|---|---:|---:|---|
| feature/v1-performance-report | 85 | 37 | Highly diverged; never wholesale merge |
| fix/student-auth-private-uploads | 27 | 2 | Significant security work; review file-by-file |
| audit-curriculum-migration | 11 | 38 | Migration work needs dependency reconciliation |
| docs/production-registration-architecture | 4 | 52 | Historical documentation branch; substantial divergence |
| docs/extraction-audit-status | 1 | 44 | Historical documentation branch |
| docs/feb-2027-tuition-improvia-launch-plan | 1 | 35 | Historical launch-plan branch |
| docs/ai-development-guidelines | 0 | 6 | Ancestor of master at audit time; closest low-divergence existing documentation branch |

The feature/v1-performance-report comparison was observed as 85 commits ahead and 37 behind. The security branch fix/student-auth-private-uploads was observed as 27 ahead and 2 behind. The audit-curriculum-migration branch was observed as 11 ahead and 38 behind.

These numbers are snapshots and may change. A branch being ahead is not proof its changes are correct, tested or safe.

### 7.4 PR #31 — key contents and release warning

PR #31 describes:

- Permanent student login with password hashes and one-time activation links.
- Teacher-issued activation links.
- Blocking guest Student_ID creation and anonymous assessment/report access.
- Approved registration mapped to verified curriculum/enrollment.
- Immutable submitted attempts and duplicate submission protection.
- Atomic unanswered-response materialisation.
- Authenticated handwritten-image proxy and Cloudinary authenticated delivery for new cloud uploads.
- Two-page report, readiness checks, scoring, diagnosis and longitudinal comparison.
- Production schema guard and read-only-by-default migration 006.
- Migration 005 audit and corrected upsert SQL.
- MySQL-backed CI and a full HTTP exam smoke workflow.

Its PR description records a successful GitHub Actions run and explicitly warns that production Aiven migration, backup/restore, Render deployment and Cloudinary configuration were not verified. CI success must not be treated as production sign-off.

### 7.5 PR #35 — key contents

PR #35 describes:

- Failed-login counter reset after expired lockout.
- Login lockout regression tests.
- Teacher access-link authentication/authorisation tests.
- SHA-256 token storage checks.
- Stronger migration schema auditing for column types, primary/foreign keys, cascade behaviour and indexes.
- Isolated SQLite migration audit tests.

Its description reports 255 tests passed and 5 warnings, but this is PR-reported evidence and was not independently rerun in this audit. It explicitly leaves AUTH-01 and AUTH-04 unchanged.

### 7.6 Reconciliation strategy

1. Compare PR #31 unique work against current master at file and function level.
2. Compare PR #35 security work and identify overlap with #31.
3. Reconcile PR #28 migration 005 audit and dependencies.
4. Inspect the actual migration chain and current production history read-only.
5. Preserve unique tests and useful code from every branch.
6. Identify duplicate or conflicting route, auth, storage and report implementations.
7. Produce one approved, small, reversible implementation plan.
8. Do not merge PR #31, #35 or #28 wholesale.
9. Do not delete branches, close PRs, rebase, force-push or rewrite history without explicit approval.

---

## 8. Prioritised development roadmap

### Phase 0 — Security and release hardening

**Estimate: 20–30 focused engineering hours**

- Reconcile PR #31, #35 and #28.
- Verify student and teacher authentication.
- Verify student ownership on attempts, submissions, uploads, reports and results.
- Verify private durable handwritten-answer storage.
- Verify CSRF coverage and session settings.
- Verify server-side timers and attempt-state transitions.
- Verify idempotent submission and evaluation.
- Verify upload validation and failure handling.
- Verify secrets/configuration.
- Verify schema and migration history.
- Establish backup and restore evidence.
- Review privacy/guardian-consent and retention requirements.

**Exit condition:** No unresolved critical student privacy, authentication, access-control or assessment-integrity blocker.

### Phase 1 — Complete the founder-operated assessment loop

**Estimate: 20–30 focused engineering hours**

- Registration review and permanent Student_ID reuse.
- Student activation/login.
- Eligibility checks.
- Assessment start and server-controlled timer.
- Answer save and resume after refresh.
- Handwritten answer upload.
- Submission preview and receipt.
- Teacher submission queue.
- Human marking and comments.
- Partial evaluation and safe re-evaluation.
- Report readiness only after required marking is complete.

**Exit condition:** A synthetic test student can complete the assessment without manual database intervention, and a teacher can evaluate it through the interface.

### Phase 2 — Diagnosis and report correctness

**Estimate: 15–25 focused engineering hours**

- Define score, percentage, attempt rate and accuracy precisely.
- Validate partial-mark calculations.
- Validate chapter/topic totals.
- Correct recurring-error detection across distinct assessments.
- Verify C01–C09 evidence and comments.
- Ensure unanswered questions do not imply conceptual weakness.
- Validate marks-lost calculations.
- Reconcile HTML and PDF report implementations.
- Ensure reports are private and understandable.
- Build golden report fixtures with hand-calculated expected results.

**Exit condition:** Every reported figure matches independently calculated examples, and recommendations are traceable to observed evidence.

### Phase 3 — End-to-end testing and deployment

**Estimate: 15–25 focused engineering hours**

- Run focused tests and full suite safely.
- Run MySQL integration tests in an isolated environment.
- Run registration-to-report smoke workflow.
- Test anonymous, owner, other-student, teacher and unauthorised-teacher access.
- Test refresh/resume, expiry, double submit and concurrent requests.
- Test valid/invalid/oversized/missing uploads.
- Test partial marking, multiple error codes and report totals.
- Test migration once and twice in disposable DB.
- Verify CI executes core exam tests rather than silently excluding them.
- Verify Render/Aiven/Cloudinary settings.
- Verify backup/restore and rollback procedures.
- Complete release checklist and manual smoke tests.

**Exit condition:** The complete workflow passes in a production-like environment with no unresolved critical failures.

### Phase 4 — Supervised pilot

**Duration: 2–4 weeks after release gates**

- Start with approximately 5–10 supervised students.
- Use synthetic data for engineering tests; use real student data only after privacy/consent controls are in place.
- Founder manually evaluates handwritten work.
- Hand-check every report.
- Measure marking time and support workload.
- Ask students/guardians to explain the diagnosis in their own words.
- Observe whether recommended practice is completed.
- Measure return for the next assessment.
- Record privacy, reliability, report-quality and usability issues.
- Do not expand towards 20–30 paying students until evidence supports it.

**Exit condition:** The workflow is reliable and the report creates enough value for students/guardians to return.

---

## 9. End-to-end acceptance workflow — Golden Workflow

The MVP must pass this complete workflow:

1. **Registration:** Student submits registration; the founder/admin reviews it; the system creates or reuses a permanent Student_ID.
2. **Authentication:** Student activates an account and logs in. Anonymous access to private assessment records is denied.
3. **Eligibility:** Student sees only assessments matching approved board, class, subject and enrollment.
4. **Assessment:** Student starts an eligible assessment. Server records start time and deadline.
5. **Answering:** Student answers questions; each save is persisted and ownership-checked.
6. **Resume:** Student refreshes or reconnects; the same attempt resumes with server-calculated remaining time.
7. **Handwritten work:** Student uploads permitted pages; invalid and oversized files are rejected; files remain private.
8. **Submission:** Student sees unanswered/required-upload preview; submission is atomic and idempotent; a receipt is shown.
9. **Evaluation:** Teacher sees the authorised submission, marks subjective work, selects evidence-backed C01–C09 codes and writes comments.
10. **Partial evaluation:** Incomplete marking is clearly represented; a final report is not incorrectly marked complete.
11. **Diagnosis:** Score, chapter/topic analysis, marks lost and recurring errors are calculated deterministically.
12. **Report:** Student receives a private, readable HTML/PDF report after required evaluation is complete.
13. **History:** The result is added to the student's performance history.
14. **Practice:** The system recommends a specific next step based on observed errors and available practice.
15. **Reassessment:** Student completes a later comparable assessment.
16. **Improvement comparison:** The system compares results accurately and avoids claiming improvement without comparable evidence.

**MVP acceptance target:** Every step works reliably, and the important success/failure paths are covered by tests.

---

## 10. Required test matrix

| Area | Minimum cases |
|---|---|
| Authentication | Anonymous, valid student, invalid password, lockout, activation expiry, logout/session clearing |
| Authorisation | Owner, other student, authorised teacher, unauthorised teacher, admin |
| Registration | New student, returning student, duplicate submission, invalid eligibility, retry |
| Assessment | Eligible/ineligible student, start, active attempt, refresh/resume |
| Timer | Server deadline, expiry, client clock manipulation, refresh, timeout |
| Submission | Normal submit, double submit, concurrent submit, missing required upload, unanswered questions |
| Upload | Valid, invalid type, spoofed MIME, oversized, malformed, missing file, deletion, retry |
| Privacy | No public raw file access, cross-student image denial, report denial, no sensitive URL leakage |
| Evaluation | Full marks, zero, partial marks, invalid marks, multiple codes, comments, partial completion, re-evaluation |
| Diagnosis | Hand-calculated score, accuracy definition, chapter totals, recurring errors across distinct tests, unanswered question |
| Reports | Awaiting evaluation, complete report, PDF generation, private delivery, history comparison |
| Migration | Correct dependency order, read-only audit, apply once, apply twice, rollback/restore rehearsal |
| Operations | Production configuration guard, health check, backup, restore, deploy rollback |

Do not delete, skip or weaken valid tests to obtain a green build. Report exact commands, pass/fail counts, skipped tests and environment limitations. A unit-test pass does not prove production readiness.

---

## 11. Commercial MVP versus later SaaS

### Required for the initial founder-operated MVP

- Student registration and login.
- Teacher/admin access.
- Eligibility and assessment creation.
- Online examination and answer persistence.
- Handwritten submissions with private storage.
- Human marking and error codes.
- Accurate diagnosis.
- HTML/PDF report.
- Student history and basic practice recommendation.
- Secure deployment, backup/restore, privacy and support processes.

### Defer until the core loop is proven

- Parent dashboard.
- Tutor/coaching dashboard.
- Online payments and subscription management.
- Advanced messaging automation.
- Multi-tenant institutional SaaS.
- Advanced analytics dashboard.
- Mobile application.
- Fully adaptive test generation.
- Handwriting OCR.
- AI-assisted evaluation.
- Additional boards/subjects beyond validated scope.

AI-assisted evaluation, if considered later, must remain a human-confirmed suggestion workflow. It requires benchmark testing against human-marked reference answers, uncertainty handling, consent/privacy review and explicit approval. Unsupervised AI grading is not approved.

### Commercial validation

- Treat ₹49 per additional assessment/report as a pricing hypothesis, not validated pricing.
- A free first assessment may reduce adoption friction, but its effect must be measured.
- Registration or free-test completion does not prove willingness to pay.
- Measure marking time, hosting/storage, messaging, payment fees, refunds, tax, support and acquisition cost.
- Do not claim profitability, retention or score improvement without evidence.
- Obtain permission before using student work, quotes, results or testimonials in marketing.

---

## 12. February 2027 target schedule

This is an ambitious working schedule from the 15 November 2026 audit date, subject to release gates and available weekly time.

| Period | Target |
|---|---|
| 16–30 November 2026 | Branch reconciliation, security and migration review |
| 1–15 December 2026 | Student workflow, authentication, attempt and submission integrity |
| 16–31 December 2026 | Manual evaluation, diagnosis and reports |
| 1–15 January 2027 | Integration tests, CI and deployment verification |
| 16–31 January 2027 | Internal/synthetic end-to-end testing and controlled readiness review |
| February 2027 | Closed supervised student pilot, only if all release gates pass |

A public commercial launch must not be promised solely because the calendar target has arrived. Security, privacy, test, backup/restore and end-to-end acceptance gates take precedence.

---

## 13. Recommended work order from this audit

1. Freeze non-essential feature expansion.
2. Re-read current repository instructions before each task.
3. Re-check current master, local Git status, branches, PRs, migrations and CI.
4. Reconcile #31, #35 and #28 at code level without blind merges.
5. Identify the first confirmed release blocker from source and tests.
6. Write a formal ten-point implementation plan for that blocker.
7. Wait for explicit approval before code changes.
8. Implement a small, reversible change on the authorised branch.
9. Add regression tests and run the relevant suite safely.
10. Hand off exact files, diff, commands, results and rollback notes.
11. Repeat until the Golden Workflow passes.
12. Run a supervised pilot before expanding scope.

---

## 14. Explicit non-goals and safety boundaries

- No production Aiven migration without separate explicit approval.
- No destructive database writes or production seed operations.
- No public exposure of private student uploads, submissions or reports.
- No real student data in commits, logs, screenshots or unapproved third-party services.
- No unsupervised AI grading.
- No automatic publication of unverified extracted questions.
- No branch deletion, PR closure, merge, rebase, force-push or history rewrite without specific approval.
- No unrelated tuition-centre website, referral, payment, credits or ingestion expansion within a security/release task.
- No assumption that documentation equals implementation.
- No assumption that a PR's reported tests were independently verified by this audit.

---

## 15. Audit conclusion

Improvia has a substantial foundation: question-bank and curriculum structures, assessment routes, answer handling, teacher evaluation, diagnostic logic and reporting foundations. The next stage is not to add more technology. It is to reconcile the best existing work, prove privacy and integrity, complete the assessment-to-report workflow, and validate that students find the diagnosis useful.

**Recommended target:** a secure, founder-operated MVP in an estimated 8–12 weeks of focused development, followed by a 2–4 week supervised pilot. A broader commercial SaaS should follow only when pilot evidence justifies it.

The decisive product question is:

> Do students and guardians find the diagnosis useful enough to practise, return for another assessment, and see measurable improvement?

Until the platform can answer that reliably, the priority remains stabilisation, not expansion.

---

## 16. Source references

Repository sources reviewed or used for this report:

- [Repository README](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/blob/master/README.md)
- [Repository development instructions](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/blob/master/docs/CHATGPT_INSTRUCTIONS.md)
- [AGENTS.md](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/blob/master/AGENTS.md)
- [Commercial Platform Roadmap](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/blob/master/docs/IMPROVIA_COMMERCIAL_PLATFORM_ROADMAP.md)
- [February 2027 launch plan](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/blob/master/docs/FEB_2027_TUITION_IMPROVIA_LAUNCH_PLAN.md)
- [PR #31 — V1 end-to-end hardening](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/31)
- [PR #35 — Student authentication and migration security](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/35)
- [PR #28 — Migration audit](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/28)
- [PR #32 — Local-only Groq extraction prototype](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/32)
- [PR #24 — AI JSON upload errors](https://github.com/Megha-2-Paul/edtech-mathematics-assessment/pull/24)

**Audit baseline reminder:** All code-level observations refer to the inspected GitHub master snapshot at 1038a2cb9540b953a2a84452fba90dcd771ffe7d. Re-run the audit against the latest master and inspect local uncommitted changes before implementation.
