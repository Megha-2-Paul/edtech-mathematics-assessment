# Improvia: Review, Risks and Improvement Backlog (v2)

**Project:** Improvia Mathematics Assessment & Improvement System  
**Repository:** Megha-2-Paul/edtech-mathematics-assessment  
**Review date:** 26 October 2026  
**Execution rule:** Work on the existing `master` branch unless the maintainer explicitly changes this instruction. Do not create new branches for this plan. Verify code-level findings against the current repository before changing behavior.

## Operating principle

Maths papers are predominantly subjective and handwritten. Handwritten evaluation is the core workflow, not an optional add-on. A typical pilot paper may carry 20 or more marks. Phase 1 uses founder-led manual marking with zero additional evaluator cash cost; later phases may use AI-assisted suggestions and paid evaluators, but a human confirms every subjective mark.

## Status at review

| Area | Status | Confidence / next proof |
|---|---|---|
| Student exam UI: timer, navigation, answers | Implemented foundation | End-to-end test required |
| Handwritten answer upload | Path exists; privacy/persistence risk | P0 blocker |
| Teacher/admin: question bank and test builder | Implemented foundation | Real-data tests |
| Manual marking and C01–C09 error codes | Foundation exists | Measure marking speed and validate rubric |
| Diagnosis and reports | Logic exists | Compare against hand-calculated examples |
| Registration and eligibility | Controlled flow exists | Live webhook and idempotency tests |
| PDF / AI JSON / manual question ingestion | Substantial foundation | Benchmark quality |
| Render + Aiven production topology | Documented | Verify live settings and restore a backup |
| AI-assisted evaluation | Not started / planning | Never autonomous; human confirmation required |
| Tuition site and integration | Planning only | Not implemented |
| Demand and willingness to pay | Hypothesis | Validate with real students |

**Overall:** pre-launch. Closed supervised testing with synthetic data only until P0 privacy, configuration, timer, migration and backup risks are resolved. Do not use real student handwritten work in public production until the release gates pass.

## Strengths to preserve

- Customer promise: “Find out exactly where you're losing marks.”
- Longitudinal diagnosis across tests rather than score-only mock tests.
- Error taxonomy: C01 Calculation; C02 Conceptual; C03 Formula; C04 Sign; C05 Incomplete steps; C06 Wrong method; C07 Missing justification; C08 Misunderstood question; C09 Time/attempt.
- Sparse-evidence rule: blank answers do not automatically prove conceptual weakness.
- Explainable, rule-based recommendations before advanced AI.
- Flask/SQLAlchemy foundation, canonical taxonomy/migrations, ingestion provenance and duplicate fingerprinting, approval-gated registration, CI and clear separation of built/planned/unverified features.
- Defer mobile apps, marketplace, credits and autonomous grading until the core loop works.

## P0 — Must resolve before public use

1. **Private handwritten images:** verify storage durability; use private object storage and short-lived signed access where supported; remove/restrict direct public upload serving; test anonymous, cross-student and authorised teacher access.
2. **Exam integrity:** store `started_at` and server-computed deadline; enforce expiry server-side; ensure submit is idempotent and attempt state transitions are one-way.
3. **Secrets and production configuration:** remove development fallback secrets from production paths; fail startup safely when required production secrets/database configuration are absent; rotate credentials if exposed.
4. **Student data / AI privacy:** no third-party AI processing of children's handwritten work until parental consent, provider retention/training terms, data location, deletion and image de-identification have been reviewed.
5. **Database migrations:** reconcile overlapping migration PRs #28 and #31 into one ordered chain; dry-run against a disposable production copy; backup first and demonstrate restore.
6. **Release evidence:** verify private report/image permissions, backup restore, registration idempotency and the full registration → attempt → answer → upload → submit → evaluate → report flow.

## P1 — Required for a controlled founder-marked pilot

- Include `test_exam_platform.py` in CI after fixing any environment/test setup issues.
- Add realistic MySQL end-to-end tests and golden-file report tests using hand-calculated expected marks/error codes.
- Build a per-question marking screen: show rubric/question and anonymised answer image; mark entry; multi-select C01–C09; saved comment phrases; re-upload request.
- Mark by question across a batch where practical; log minutes per question and paper from day one.
- Add phone-first upload guidance, image quality checks, explicit “not attempted”, submit preview, safe resume/autosave and accessible controls where absent.
- Create worked solutions, a three-item plain-language fix list, exemplar answers and a parent-friendly summary.
- Prepare consent/privacy notice, secure report delivery and re-upload/recheck workflow.
- Pilot one board, one class and one subject first; recommended validation cohort is about 10 students from the planned tuition cohort, with a short ~20-mark paper adjusted to actual marking time.

## Student workflow backlog

### Before the test
- Simple sign-in/identity process; OTP only if secure and feasible.
- Device/connection/upload readiness check and an untimed practice question.
- Writing guide showing full-mark working, labelled steps and boxed final answer.
- Reminder with date, duration, rules and working link.

### During the test
- Autosave with server as source of truth; safe resume to same attempt and remaining time.
- Warnings at 10, 5 and 1 minutes; clear expiry message.
- Answered/unanswered/flagged/current question states.
- Per-question page upload, image guidance, compression/rotation/cropping and diagram support.
- Mobile maths keypad if it can be implemented without compromising reliability.
- “Not attempted” state and a submit preview listing unanswered/unphotographed questions.

### After the test
- Submission receipt with attempt ID and no duplicate results.
- Clear expected marking turnaround.
- Evaluator can request a replacement photo for unreadable work.

### Accessibility
- Phone-first responsive design, large touch targets, contrast, keyboard/screen-reader labels and low-bandwidth behavior.
- Consider Bengali/Hindi labels after the core English workflow is stable.

## Evaluation policy and phases

**Invariant:** every subjective mark delivered to a student must be confirmed by a human. AI can suggest transcription, marks, error codes and reasons, but it must not finalise marks.

| Phase | Workflow |
|---|---|
| 1 — founder-marked | Automatic rule-based objective checks; founder reads handwritten work and confirms all marks; log time per paper. |
| 2 — hybrid low-cost | A free/local/hosted model may suggest transcription, marks, error codes and a reason; founder accepts/edits/rejects every item. |
| 3 — scaled | Paid model may provide a first pass and confidence scores; trained evaluators confirm all low-confidence items and a calibrated sample; regular re-calibration. |

Rules:
- Mark by question where practical, not only by whole paper.
- Build a gold set of 20–30 carefully marked papers before trusting a new AI version; initial pilot may begin with 10–20.
- Compare AI suggestions with founder marks and record agreement; set an acceptance threshold before use.
- Keep a reason/step reference for every suggestion and audit who changed a mark, when, and why.
- Use OCR like Tesseract only for printed/simple text, not as reliable handwritten maths understanding.
- Before any third-party AI processing of children's work: obtain parental consent that names the provider and purpose; review retention/training terms; remove/crop names and IDs; confirm data location and deletion process.
- Estimate AI cost only after the gold-set benchmark establishes image volume, escalation rate and time saved.

## Learning value after evaluation

1. Worked solutions once the assessment closes.
2. Three-item plain-language fix list tied to exact questions, not just raw codes.
3. Mistake notebook for wrong/unattempted questions.
4. Optional confidence check (“sure / unsure / guessed”) to distinguish careless mistakes from knowledge gaps.
5. Time per question alongside marks where measured reliably.
6. Rubric feedback by method, working, presentation and final answer.
7. Exemplar full-mark and partial-mark answers.
8. Parent summary: strongest area, main weakness and one next action.
9. Targeted practice set of 5–8 questions for the top weakness/error.
10. Progress view across Test 1 → Test 2 → Test 3.

## P1/P2 robustness, operations and scale

- Role-based access; students see only their own records; evaluators see assigned work; log administrative actions.
- CSRF protection for state-changing routes, security headers and rate limits for login/uploads.
- Privacy notice, retention/deletion policy, applicable parental consent and incident process; delete raw images after a defined retention period while retaining required marks/error codes.
- Staging environment mirroring production, health checks, uptime/error alerts, safe error pages, background jobs and retry/delivery logs.
- Compress/resize uploaded images; generate marking thumbnails; paginate lists; index foreign keys/common queries; cache published question bank where appropriate.
- Stable question IDs for longitudinal analysis.
- Test sparse data: no attempt, partial marking, ties, single-question tests; PDF long comments/multiple errors/page breaks/missing images; migrations idempotent/in order and subject-scoped.
- One canonical question publication path with human approval and rights/source status. Benchmark 20–30 real papers; retain PyMuPDF as default unless another parser demonstrably wins; flag uncertain taxonomy mapping.

## Business and validation plan

- Start with one cohort, preferably the planned Behala tuition cohort of about 10 students; do not open to the public before P0 gates.
- Suggested initial test: ICSE Class 10 Mathematics only, if the founder confirms that choice. Resolve disagreement between wider CBSE/ICSE Class 10–12 business ambitions and broader pilot documents before public marketing.
- A free worksheet may lead to a “where are you losing marks?” diagnostic.
- Pause non-essential integrations (Groq extraction, cloud sync, URL ingestion, Shaalaa parser, MarkItDown replacement, credits and tuition-site integration) until the core loop works.
- Pricing sequence: free supervised pilot → low-cost diagnostic → test willingness to pay again → only then consider a subscription.
- Referrals only after the student has received a useful report.
- Record consent for messaging, parental authorisation where applicable and AI-assisted marking.

### Metrics
- Registration → test start rate.
- Start → submission rate.
- Upload success and re-upload rate.
- Report delivered/viewed within 48 hours.
- Second-test rate (most important repeat-value signal).
- Student/parent usefulness rating.
- Founder/evaluator minutes per paper and per question.
- AI-human agreement rate once AI is introduced.
- Cost per completed diagnostic and acquisition cost by channel.
- Willingness to pay, repeat payment, referrals and refunds/corrections.

## Branch/PR cleanup

1. Freeze non-essential features until P0 is closed.
2. Reconcile PR #31 and PR #28 into one migration chain.
3. Resolve the URL/Shaalaa stack (PR #4/#5) in order, or defer.
4. Choose one sync design (PR #9) or drop it.
5. Benchmark MarkItDown (PR #6) against PyMuPDF; close if superseded.
6. Validate malformed JSON guidance (PR #24) against varied inputs.
7. Benchmark Groq (PR #32) on real papers before deciding.
8. Delete historical branches only after checking for unique commits/docs.
9. Tag a pilot release only after P0 checks pass.
10. Do not create new branches for this backlog or implementation unless the maintainer explicitly asks.

## Roadmap

### Phase 0 — Secure and stabilise (now through late November 2026)
- [ ] Private durable answer-image storage and access tests.
- [ ] Restrict/remove direct upload route; verify ownership checks.
- [ ] Server-authoritative timer and idempotent submission.
- [ ] Production startup fails safely without secure configuration.
- [ ] Reconcile migration PRs; dry run on disposable production copy.
- [ ] Verify backup and complete one restore.
- [ ] Include exam-platform tests in CI.

### Phase 1 — Founder-marked pilot build (December 2026–January 2027)
- [ ] Per-question photo upload guidance and “not attempted”.
- [ ] Per-question marking UI, rubric, codes and comment phrases.
- [ ] Phone-first exam flow with autosave/resume and safe timer.
- [ ] Disposable-student end-to-end test.
- [ ] Golden-file report tests.
- [ ] Worked solutions, fix list, rubrics and exemplar answers.
- [ ] Consent/privacy notice and marking-time tracking.

### Phase 2 — Pilot and calibration (February 2027)
- [ ] Closed pilot with about 10 tuition-cohort students.
- [ ] Founder marks every paper and logs time.
- [ ] Create a gold set of 10–20 papers.
- [ ] Collect student/parent usefulness feedback.
- [ ] Decide whether a second test and paid diagnostic are justified.

### Phase 3 — Hybrid evaluation
Only after pilot evidence and privacy conditions:
- [ ] Test a free/local option on the gold set.
- [ ] AI suggests; founder confirms every mark.
- [ ] Record agreement and time saved.
- [ ] Continue only if the workflow saves enough time without reducing reliability.

### Phase 4 — Paid scale
Only when volume justifies it:
- [ ] Recruit/calibrate evaluators.
- [ ] Consider paid AI with confidence scores.
- [ ] Human review of all uncertain items and a calibrated sample.
- [ ] Regular recalibration, monitoring and load tests.
- [ ] Add boards/classes/subjects one at a time.

## Open decisions for the founder

1. First payer: student directly or parent?
2. Pilot: ICSE Class 10 Mathematics only, or CBSE from the beginning?
3. How many papers per week can the founder mark, and how many minutes per paper?
4. First paper length: 20 marks or shorter?
5. English-only interface first, or Bengali/Hindi labels?

## Scope and evidence boundary

This is a planning backlog, not proof that every listed risk exists in the current code. Verify code-level claims against the current `master` branch before implementing. Pricing, costs, AI accuracy and demand are hypotheses to measure. Do not claim that code was executed or live production was tested unless that actually happened.
