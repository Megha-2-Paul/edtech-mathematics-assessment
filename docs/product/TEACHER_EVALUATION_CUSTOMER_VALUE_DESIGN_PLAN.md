# Improvia Teacher Evaluation and Customer Value Design Plan

**Status:** Approved product/design plan; implementation has not started.
**Repository:** `Megha-2-Paul/edtech-mathematics-assessment`
**Target branch:** `master` for this documentation save only. Future implementation must follow the repository's branch/PR workflow and be approved in small increments.
**Purpose:** Make teacher evaluation trustworthy and turn assessment results into useful, evidence-based student improvement.

## 1. Product goal

Improvia is not merely a mock-test platform. Its central promise is to help students understand:

1. Where they lost marks.
2. Why they lost those marks.
3. What they should practise next.
4. Whether they improve after practising.

The product loop is:

**Registration → Assessment → Submission → Teacher Evaluation → Error Diagnosis → Student Report → Personalised Practice → Reassessment → Progress Comparison**

Customer value and assessment integrity are co-equal requirements. Correct scoring without actionable next steps is insufficient; attractive recommendations built on unreliable marking are unacceptable.

## 2. Design principles

- Human-controlled marking remains authoritative. Do not implement unsupervised AI grading.
- Treat existing code behaviour as unverified until checked against current `master`, tests, migrations, and database behaviour.
- Distinguish implemented code, documented intent, planned design, tested behaviour, and live production behaviour.
- Preserve the existing C01–C09 Mathematics error taxonomy unless repository evidence and an explicitly approved decision justify a change.
- A blank answer alone does not establish a conceptual weakness.
- Student names, submissions, handwritten images, marks, reports, and histories are private; enforce authorisation at every relevant route.
- Never send real student work to a third party or AI provider without explicit authorisation and appropriate consent/privacy checks.
- Never run unapproved migrations or writes against production Aiven.
- Do not expand to more subjects, classes, automation, or dashboards before the core loop is dependable and the pilot demonstrates value.
- All behaviour changes require tests; report exact commands and actual results.

## 3. Priority order

### Priority 1 — Trust and student privacy

Verify and, where confirmed necessary, fix:
- Teacher access to evaluation routes.
- Student ownership and teacher authorisation for answer images, submissions, reports, and results.
- Private storage and access control for local and legacy cloud-hosted handwritten work.
- CSRF coverage for state-changing routes.
- Numeric mark validation and safe error handling.
- Server-side completion/finalisation rules so incomplete work is not presented as a final result.

Access-control checks are release-blocking if a real unauthorised access path is confirmed.

### Priority 2 — Marking integrity and consistent metrics

Establish one authoritative scoring contract and avoid duplicated score calculations across modules. Define and test:
- Score: sum of awarded marks over the evaluated question set.
- Total possible marks: sum of maximum marks for that same question set.
- Percentage: score divided by total possible marks, rounded only for display.
- Marks lost: total possible marks minus score, presented as final only when the evaluation is complete.
- Attempt rate: answered questions divided by total questions; the precise treatment of explicitly confirmed unanswered questions must be documented consistently.
- Accuracy: fully correct answered responses divided by answered responses; partial-credit responses are not fully correct. If there are no answered responses, show “N/A” rather than misleading 0%.
- Partial marks, zero marks, zero possible marks, malformed values, out-of-range marks, and supported mark increments.

Prefer exact decimal or integer half-mark arithmetic if compatible with the current schema and marking rules. Check the existing schema before deciding.

### Priority 3 — Evaluation lifecycle and auditability

Audit the current implementation before committing to a new schema. Target behaviour should ensure:
- Teacher drafts do not affect student-facing reports or longitudinal history.
- A question is explicitly classified as marked, unanswered (teacher-confirmed omission), or pending.
- Server-side finalisation is blocked until every question has a valid terminal state.
- Corrections are traceable and do not silently rewrite the historical basis of a previously released report.
- Repeated saves and retries cannot inflate question history or create duplicate evaluation records.
- Related finalisation writes are atomic where required, with failures recoverable and tested.

Claude proposed immutable, versioned finalised evaluations and report snapshots. This is a candidate design, not a mandatory rewrite. Compare it with the current tables and migrations first; choose the smallest architecture that gives reliable finalisation, correction history, and reproducible reports.

A submission-time snapshot of question text, maximum marks, answer key, and marking guidance may be needed so later question-bank edits cannot change how an old attempt is interpreted. Verify what is already stored before proposing schema changes.

### Priority 4 — Reliable diagnosis

- Keep C01–C09 as the current Mathematics taxonomy:
  - C01 Calculation
  - C02 Conceptual
  - C03 Formula
  - C04 Sign
  - C05 Incomplete steps
  - C06 Wrong method
  - C07 Missing justification
  - C08 Misunderstood question
  - C09 Time/attempt issue
- Multiple error codes may be recorded for one response, but marks lost must be counted once at response level, never duplicated across codes.
- A code occurrence count and a marks-lost attribution are different measurements. If per-code marks-lost attribution is unavailable, state that limitation rather than inventing a split.
- Avoid chapter strength/weakness labels without a defined evidence floor. A candidate starting rule is at least three evaluated questions plus a minimum possible-mark threshold; validate this before adoption.
- Label insufficient evidence as “not enough evidence yet,” including the supporting sample count.
- A “recurring error” should require the same code in at least two distinct finalised submissions, not just repeated saves or a single attempt.
- Compare results only when the subject and assessment basis are comparable. When totals or question sets differ, avoid misleading raw-score trend lines and explain limitations.
- Recommendations should be short, ordered, actionable, and linked to the evidence that triggered them.

### Priority 5 — Student improvement and customer value

Every released report should help answer “What happened?”, “Why did it happen?”, and “What should I do next?”

Target student-facing value:
1. **Question-level feedback:** marks awarded/available/lost, teacher comment, and relevant submitted work where access is permitted.
2. **Plain-language explanation:** explain the selected error category with reference to the student's actual work. Do not infer a conceptual weakness from an unanswered question.
3. **Specific practice:** recommend a small, manageable set of verified question-bank items related to the diagnosed issue, with suitable chapter and difficulty metadata.
4. **Reassessment:** where practical, use new comparable questions to test the targeted skill after practice.
5. **Evidence of progress:** show changes in targeted errors and performance over comparable assessments, alongside sample sizes and limitations.
6. **Parent clarity:** make priorities, completed practice, and progress understandable without technical analytics jargon.

Recommendations should initially be deterministic, transparent, and teacher-controlled. No expensive adaptive-learning system or AI grading is required to validate this value proposition.

### Priority 6 — Teacher and parent experience

- Measure teacher time per submission before optimising for speed.
- Keep the pilot workflow simple and phone-friendly, with clear validation errors and a visible evaluation status.
- Consider a marking queue, draft autosave, stale-edit detection, and a simple claim/lock only if current workflow evidence shows they are needed.
- Keep teacher comments escaped as text, never rendered as HTML or Markdown.
- Reports should be concise and useful; avoid dashboards or charts that do not change the student's next action.

## 4. Pilot value validation

Use a small, supervised pilot and record evidence rather than assuming demand or outcomes.

Measure:
- Marking correctness against hand-checked examples.
- Whether students understand their mistakes and can identify the next practice action.
- Completion of recommended practice.
- Performance on new, comparable questions targeting the practised skill.
- Teacher marking and report-review time per submission.
- Student and parent report usefulness, clarity, and willingness to take another assessment.
- Where commercially relevant, repeat use, referrals, willingness to pay, and operational cost.

A higher score on a different test is not by itself proof that Improvia caused improvement. Record baseline skill, recommended practice, practice completion, reassessment result, and comparability. Treat early pilot evidence cautiously.

## 5. Golden test scenarios

Build or verify tests for at least these scenarios:
- Partial marks produce the correct score, percentage, and marks lost.
- An unanswered question is explicitly confirmed and is not assigned a conceptual error by default.
- Multiple error codes on one response do not double-count marks lost.
- Saving the same evaluation twice does not inflate history.
- Correcting an evaluation preserves traceability and updates the current report consistently.
- Invalid marks (blank where not allowed, nonnumeric, negative, above maximum, NaN/infinity, unsupported increments) are rejected before writes.
- Partial evaluations remain pending and are not shown as final reports.
- Comparisons use appropriate prior finalised attempts and do not imply unsupported trends.
- Small chapter samples show insufficient evidence rather than overconfident labels.
- Anonymous users, another student, and unauthorised teachers cannot access private work; authorised owners/teachers can access only what their role permits.
- Transaction/failure tests verify that partial finalisation does not leave inconsistent records.
- Old reports and attempts remain tied to the appropriate evaluation/question version if versioning is adopted.

Use pure, fast tests for arithmetic and a disposable real MySQL database for transaction, constraint, and persistence behaviour. Do not use production Aiven for tests.

## 6. Staged delivery

1. **Repository-backed audit:** read the repository instructions and relevant current-master code, tests, CI, migrations, open PRs and dependencies. Distinguish confirmed defects from hypotheses and product decisions.
2. **Security and ownership:** fix only confirmed release blockers with targeted access-control and upload tests.
3. **Mark validation and scoring contract:** centralise authoritative calculations and test edge cases.
4. **Completion and correction lifecycle:** make pending/unanswered/marked states and server-side finalisation rules explicit; choose the smallest safe design after schema review.
5. **Idempotent history and comparable diagnosis:** derive history from authoritative evaluated state where practical; introduce evidence floors and honest uncertainty labels.
6. **Report reproducibility:** ensure released reports use a stable evaluation basis and deterministic, testable rules. Add immutable versions/snapshots only where justified by the audit.
7. **Practice and reassessment loop:** deliver targeted verified practice and collect pilot evidence of skill improvement.
8. **Usability and pilot measurement:** measure marking time, feedback usefulness, practice completion, and student/parent response before expanding scope.

Each stage is a separate, small, reversible task with its own approved plan and tests. Do not begin the next stage automatically.

## 7. Database, migration, and release safeguards

- Inspect actual migration history and schema before proposing any migration; do not infer live schema from docs.
- Every schema change needs a new correctly numbered migration, dependency review, idempotency considerations, tests, and rollback notes.
- No production Aiven migrations or writes are authorised by this plan.
- Do not merge PR #31 or PR #35 on the strength of a review summary. Reconcile their actual diffs, dependencies, and tests against current master first.
- Preserve existing local work and do not blindly pull/reset/clean a dirty working tree.
- Do not create a new implementation branch until the repository's branch-limit and open-PR rules have been checked and reconciled.

## 8. Scope explicitly deferred

Until the core loop is validated, do not add:
- Unsupervised AI grading.
- AI processing of real student work without explicit approval and consent/privacy checks.
- Broad automated/adaptive learning infrastructure.
- Cross-subject comparisons or diagnostic codes forced across unrelated subjects.
- Multiple-teacher coordination features unless a demonstrated pilot need justifies them.
- Unnecessary dashboards, charts, or question-bank expansion unrelated to the confirmed release blockers.
- New classes/subjects as a substitute for validating student value.

## 9. Definition of success

The core is ready for a controlled pilot only when:
- Student submissions, images, reports, and results are correctly access-controlled.
- Marks, totals, percentages, and marks lost match hand-checked examples.
- Invalid marks and incomplete evaluations cannot silently produce misleading final results.
- Repeated saves and corrections do not corrupt history or create unexplained report changes.
- Student-facing diagnoses do not overstate what the evidence supports.
- Reports provide concrete next actions grounded in verified questions and teacher-approved feedback.
- The end-to-end assessment-to-report workflow has been tested, and the owner has reviewed results locally.

The customer-value loop is validated only when pilot evidence shows students understand the feedback, act on the recommended practice, and can demonstrate progress on suitable reassessments.

## 10. Next action

Start with the repository-backed audit and a formal 10-point plan for the first confirmed blocker. Do not implement the entire design in one change. The owner reviews and tests locally and approves each incremental task.
