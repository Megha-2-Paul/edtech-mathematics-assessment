# Improvia V1 Student Performance Report Specification

**Version:** 1.0  
**Audience:** Student and parent/guardian  
**Output:** Two-page downloadable PDF, with a matching in-app report  
**Purpose:** Explain observed mark loss, identify evidence-backed improvement priorities, compare progress, and guide the next assessment.

## Product principles

1. The report must answer what happened, what evidence supports it, and what to practise next.
2. Observed facts must be separated from interpretations or hypotheses.
3. Error frequency is not the same as marks lost by a particular error.
4. The first assessment is a baseline; do not invent prior comparisons.
5. Missing evaluation is not zero. A final report is available only after evaluation and data validation are complete.
6. Do not make board-exam score predictions or unsupported causal claims.

## Page 1 — Performance at a glance

- Student name and ID; class, board, subject; test title/ID, date, duration and maximum marks.
- Score and percentage.
- Attempt rate.
- Attempted-work accuracy.
- Unattempted question count and available marks.
- Chapter performance table with marks earned / available, percentage, and evidence sufficiency.
- Demonstrated strength and priority area where sufficient evidence exists.
- Short parent/student summary.

## Page 2 — Diagnosis, progress and next steps

- Evaluator-coded error patterns and number of distinct questions tagged.
- Prior-assessment coverage for error patterns.
- Previous assessment score/percentage, changes, and comparison limitations.
- Recurring-error trends across distinct assessments in the same subject/class/board scope.
- Up to three personalised recommendations with specific actions.
- Interpretation note explaining limited evidence and non-comparable tests.

## Metric definitions

- **Score:** sum of marks awarded for the current test's questions with evaluated marks.
- **Score percentage:** earned marks / official test maximum × 100.
- **Attempt rate:** explicitly attempted questions / total test questions × 100. Answered and partial statuses count as attempted; unanswered counts as unattempted. Missing response records are a data-quality failure, not assumed unattempted.
- **Attempted-work accuracy:** marks earned on attempted questions / maximum marks available on attempted questions × 100. This is a marks-based ratio, not the percentage of answers fully correct.
- **Chapter percentage:** marks earned for the chapter / marks assigned to the chapter in the assessment × 100.
- **Error frequency:** number of distinct question/code pairs tagged by the evaluator. Multiple error codes on one question must not inflate score totals.
- **Normalised error rate (future enhancement):** distinct attempted questions tagged with a code / attempted questions × 100.
- **Marks change:** current marks minus previous marks, shown only with context.
- **Percentage-point change:** current score percentage minus previous score percentage.
- **Recurring error:** same code appears in the current assessment and at least one distinct prior assessment in the same subject/class/board scope.
- Zero denominators are N/A, not zero.
- Chapter results with fewer than two attempted questions are flagged as insufficient evidence and excluded from automated strength/weakness labels.
- Prior assessments in the same subject/class/board scope but with different test IDs have limited comparability unless equivalent coverage/difficulty is verified.

## Data fields

Reuse existing students, tests, questions, attempts, responses, and evaluation_errors records. Required data includes:
- Student identity and academic context.
- Test identity, date, duration, subject/class/board and official maximum marks.
- Question IDs and marks assigned to the test, plus chapter/topic.
- Explicit response status, marks awarded, correctness, and evaluator error tags/comments.
- Prior submitted assessments and their error tags for longitudinal comparisons.

Verify existing schema and data before considering a migration. The existing evaluation_errors.marks_lost field may support evaluator-attributed deductions when populated, but it must not be inferred when multiple error codes share one answer.

## Data validation and report readiness

A final report is ready only when:
- The test has at least one question.
- Every expected question has a response record.
- Every expected response has a non-null marks-awarded value.
- The sum of question marks matches the official test maximum within 0.01.
- The official maximum is positive.

Otherwise, show a pending/data-validation state and do not offer a final PDF.

## Acceptance checklist

### Data correctness
- [ ] Correct student, test, question and response records are used.
- [ ] Earned marks reconcile with evaluated records and the official test maximum.
- [ ] Incomplete evaluation is detected and cannot silently produce a final report.
- [ ] Unattempted answers are not inferred from zero marks.

### Metric correctness
- [ ] Score percentage, attempt rate, attempted-work accuracy and chapter percentages match independent fixtures.
- [ ] Zero denominators produce N/A.
- [ ] Multiple error codes do not double-count score totals.
- [ ] Error frequency is not presented as marks lost without explicit attribution.

### Diagnosis and progress
- [ ] Every finding is traceable to question-level evidence or a defined calculation.
- [ ] First assessment is labelled baseline.
- [ ] Recurring errors require evidence across distinct assessments.
- [ ] Incomparable tests and insufficient chapter evidence are flagged.

### PDF and privacy
- [ ] PDF is exactly two pages and readable on mobile.
- [ ] No clipped/overlapping content.
- [ ] PDF contains only the intended student's data.
- [ ] A report-generation failure cannot produce a false success/delivery confirmation.

## V1 exclusions

AI handwriting grading, predicted board-exam scores, causal claims unsupported by evaluated work, adaptive question selection, parent dashboards, and marks-lost attribution without explicit evaluator input.
