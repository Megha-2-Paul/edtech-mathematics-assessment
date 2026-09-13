# Product Strategy

## Positioning

This project is a Mathematics Assessment & Improvement System for CBSE/ICSE Classes 10–12 in India.

It should not be positioned as another generic mock-test series. The central value proposition is diagnosis:

**Find out exactly where marks are being lost and what to improve next.**

Students already have textbooks, question banks, sample papers, previous-year questions, videos, coaching and online tests. More questions alone are not the strongest differentiation.

## Initial customer segments

### Serious students

Want exam practice, strict grading, feedback and progress tracking.

### Average/struggling students

Often study but remain around the middle score range. They need recurring-error, chapter and accuracy analysis and clear next steps.

### Parent-driven students

Need visible evidence of progress and accountability.

### Trial users

A low-cost diagnostic is the preferred entry point.

## Funnel

```text
Content / Search / Referral
        ↓
Low-cost or free diagnostic
        ↓
Assessment
        ↓
Diagnostic report
        ↓
Weaknesses + next focus
        ↓
Repeated tests
        ↓
Progress tracking
        ↓
Referral
```

## Validation

The first meaningful milestone is **20–30 real paying students** who complete the loop.

Important measures:

- Registration → payment
- Payment → test attempt
- Attempt → report viewed
- Test 1 → Test 2 → Test 3
- Retention
- Referrals
- Student/parent satisfaction
- Evaluation time per submission
- Cost per student
- Willingness to pay

The key question is whether students repeatedly take assessments because the analysis is useful.

## Pricing hypotheses

Initial hypotheses, not assumptions:

- Trial: ₹49–₹99
- Monthly: approximately ₹299–₹499
- Intensive: approximately ₹699–₹999/month

Actual pricing must be validated against willingness to pay, evaluation effort, acquisition cost, retention and report value.

## Differentiation

The intended differentiation is longitudinal, data-driven performance analysis:

**Attempts + marks + chapters + topics + difficulty + competency + error codes + repeated mistakes + trends**

This supports personalised recommendations rather than only a score.

## Competition and alternatives

Students can already use board material, sample papers, question banks, online tests, teacher grading, analytics tools and AI-based assessment products.

The strategy is therefore not to claim that assessment is new. The opportunity is to make **why marks are lost + improvement over time** the central product experience.

## Acquisition

Potential channels:

- Instagram / YouTube
- Google search
- WhatsApp
- Referrals
- Tutors and coaching centres
- Micro-influencers
- Relevant parent/student communities

Content should demonstrate real lost-mark patterns, marking issues, calculation/sign errors, presentation mistakes, chapter weaknesses and exam strategy.

## Research and knowledge workflow

NotebookLM is a supporting internal tool for source-grounded research and content/question development. It can help the founder work through authoritative/permitted CBSE/ICSE documents, sample papers, marking schemes, licensed material and original content.

Use it for:

- syllabus/curriculum research
- marking-scheme research
- question-bank research and classification
- assessment/content validation
- educational research and internal knowledge bases

Do not make NotebookLM a dependency of the student exam platform or production data model. It must not own grading, student records, analytics, diagnosis, recommendations or report generation. Final mathematical and assessment decisions remain validated by the business.

Start with available free/standard access; do not make a paid NotebookLM plan a prerequisite for MVP. Specific limits/features should be re-checked against Google's current documentation when needed.

See `NOTEBOOKLM_WORKFLOW.md` for the detailed operating procedure and boundaries.

## Automation strategy

Automation should reduce repetitive founder work without turning the MVP into a large software project.

The target operating model is:

> **The founder evaluates the student's mathematics once; the system performs the repetitive work around that evaluation.**

Automate early:

- Student IDs and database records
- Objective scoring
- Score/percentage/attempt calculations
- Chapter, topic and error analysis
- Longitudinal comparison and recurring-error detection
- Student-profile updates
- Charts and report generation

Keep human-controlled initially:

- Subjective mathematics evaluation
- Ambiguous answer decisions
- Final marks
- Uncertain error classification
- Question-quality decisions
- Customer support and feedback interpretation

Use n8n as an orchestration/integration layer rather than as the owner of mathematical scoring, analytics, diagnosis, authentication, exam timing or the core database model. Use Python for assessment analytics/diagnosis/reporting, MySQL as the production source of truth, and NotebookLM only as an internal research/content-support tool.

See `AUTOMATION_WORKFLOW.md` for the detailed automation matrix, tool responsibilities, priorities and V1–V5 evolution.

## MVP economics

Manual evaluation is acceptable for validation but is not the final scaling model.

For example, 100 students × 15 minutes of evaluation is 25 hours for one test cycle. The business therefore needs standardised evaluation, better workflows and eventually human-assisted automation as volume grows.

Automation should first eliminate repetitive work around evaluation rather than attempting to eliminate human mathematical judgment.

## Roadmap

### V1 — Founder-operated MVP

Flask + MySQL + manual subjective evaluation + automated Python analysis/reports.

NotebookLM is available as an internal research tool for curriculum, marking-scheme, question-bank and content research. No API integration is required.

The MVP should keep the operational stack small and prove the full assessment → diagnosis → report loop.

### V2 — Automated operations

Automated processing, report generation and communication. Add n8n orchestration where it materially reduces repeated work; standardise NotebookLM notebooks/prompts/research outputs where useful.

The target is that the founder evaluates a submission once and does not manually recalculate scores, create charts/reports, update cumulative statistics or send routine notifications.

### V3 — Productised analytics

Student dashboard and cumulative analytics, including longitudinal errors, chapter trends, recurring mistakes and improvement areas.

### V4 — AI-assisted assessment

AI-assisted handwriting/evaluation and personalised recommendations, with confidence-based human verification/exception handling. AI should assist evaluation rather than be assumed to replace human grading completely.

### V5 — Scalable assessment platform

Scalable assessment platform with tutor/school capabilities and broader workflow automation.

Do not jump to V5 before validating V1.

## Main risks

- Customer acquisition
- Differentiation
- Question quality
- Grading workload
- Retention
- Trust
- Pricing
- Seasonality
- Competition
- Founder workload
- Automation complexity
- AI grading reliability

The strategy must remain evidence-driven. Revenue, subscriptions, retention and conversion should never be assumed before measurement.
