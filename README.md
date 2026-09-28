# Mathematics Assessment & Improvement System

A low-cost assessment platform for school students focused on one question:

> **Why is a student losing marks, and what should they improve next?**

Improvia is expanding its initial pilot scope beyond the original Classes 10–12 Mathematics focus. The controlled pilot will cover **Classes 9–12 Mathematics**, with **Computer-related subjects introduced for applicable classes**, beginning with Class 10 CBSE.

This is not intended to be a generic mock-test marketplace. The product loop is:

**Test → Submission → Evaluation → Diagnosis → Report → Student Profile → Recommended Focus → Next Test → Progress**

## Current pilot scope

### Mathematics
- Class 9 — Mathematics
- Class 10 — Mathematics
- Class 11 — Mathematics
- Class 12 — Mathematics
- CBSE and ICSE where the relevant curriculum is supported

### Computer / Computer-related subjects
- Class 10 CBSE — Information Technology (Code 402)
- Class 10 CBSE — Computer Applications (Code 165)
- Additional computer subjects/classes can be added after curriculum validation.

**Important:** “Computer” should not be stored as one ambiguous Class 10 CBSE subject. The platform should distinguish **Information Technology (402)** from **Computer Applications (165)** because CBSE treats them as separate subjects. For 2026–27, CBSE's scheme of studies lists Information Technology and Computer Science/Informatics Practices as separate subject options, while the Class X sample-paper page separately lists Computer Application. citeturn0search0turn0search1

The Class 10 CBSE Information Technology curriculum (402) itself has distinct components such as Employability Skills and Subject Specific Skills, so those should be represented as curriculum structure rather than treated as generic “computer” content. citeturn0search12

## Pilot validation cohort

The first real-user pilot can use:

| Student | Assessment scope |
|---|---|
| Class 10 CBSE student | Mathematics + Information Technology / Computer subject as applicable |
| Class 9 ICSE student | Mathematics |

The purpose of this pilot is to validate the assessment → evaluation → diagnosis → report → improvement experience across more than one class, board and subject.

The pilot does **not** by itself prove demand across every class, board or subject. Expansion should continue only where students/guardians find the analysis useful and are willing to take another assessment or refer another student.

## Current MVP

- Flask-based student-facing exam website
- MCQ and subjective questions
- Subjective final-answer selection plus configurable handwritten-work upload
- Automatic answer persistence during an attempt
- Countdown timer and submission confirmation
- Duplicate-submission prevention
- Teacher/admin question-bank management
- Teacher/admin test creation
- Manual subjective evaluation
- Structured error diagnosis
- MySQL as the persistent source of truth
- Student result and performance-report views
- Cumulative question/performance history foundation
- Production deployment on Render using Aiven MySQL as the primary database
- Canonical subject/syllabus taxonomy

## Assessment philosophy

The product should not simply report:

> **62 / 80**

It should help answer:

- Where were marks lost?
- Why were they lost?
- Which mistakes are recurring?
- Which chapters/topics need attention?
- What should the student practise next?
- What changed in the next assessment?

For Mathematics, the initial diagnostic categories include calculation, conceptual, formula, sign, incomplete steps, wrong method, missing justification, misunderstood question, and time/attempt issues.

Other subjects should **not** automatically inherit the Mathematics error taxonomy. Each subject should use an appropriate evaluation/diagnosis framework.

## Current environment architecture

Development and production are intentionally separated:

```text
LOCAL DEVELOPMENT
Your PC
  ↓
Local MySQL
  ↓
Code/tests/data development

PRODUCTION
Render
  ↓
DATABASE_URL
  ↓
Aiven MySQL
  ↓
Students / Tests / Questions / Attempts / Responses / Evaluations / History
```

The production application does **not** currently require local-MySQL ↔ Aiven synchronization.

The repository also contains an optional question-bank sync layer controlled by `QUESTION_BANK_SYNC_DATABASE_URL`. This is a separate primary-to-secondary question-bank mechanism; it is not the student-registration architecture.

See `PRODUCT_WORKFLOW.md` for the current expanded product scope and pilot workflow, and `PRODUCTION_ARCHITECTURE.md` for the production registration architecture.

## Architecture

```text
Student Website
      ↓
 Flask / API
      ↓
 Aiven MySQL (production source of truth)
      ↓
 Evaluation / Analytics / Diagnosis
      ↓
 Performance Report + Student Profile
      ↓
 Next Assessment
```

Planned orchestration and communication can use n8n, Python reporting/analytics, email, and WhatsApp. These integrations are not the core exam engine.

## Data model direction

The system is designed to retain structured history at question level, including:

- Student ID and registration information
- Test ID and test metadata
- Question ID and question metadata
- Marks awarded
- Attempt/response status
- Evaluation error categories and comments
- Handwritten answer-image references
- Question history across tests
- Longitudinal performance data

This enables analysis of recurring errors rather than only reporting scores.

## Error taxonomy

For Mathematics, the initial evaluation categories are:

- C01 — Calculation
- C02 — Conceptual
- C03 — Formula
- C04 — Sign
- C05 — Incomplete steps
- C06 — Wrong method
- C07 — Missing justification
- C08 — Misunderstood question
- C09 — Time/attempt

These are an initial Mathematics framework and may evolve from real student data.

Subject-specific diagnosis should be defined separately for Computer/IT and future subjects.

## Registration status

The current controlled-launch process is:

```text
Google Form
   ↓
Google Sheets
   ↓
Manual review / confirmation
   ↓
Create or reuse permanent Student_ID
   ↓
Aiven MySQL
   ↓
Assessment access
```

Google Sheets holds raw registration and validation responses during the pilot. Aiven remains the production source of truth for enrolled students and assessment data.

## Current development stage

The platform is at the **controlled functional-testing / pre-public-launch stage**.

The immediate priority is to validate the complete assessment → evaluation → diagnosis → report loop with real students across the initial pilot scope before adding AI grading or large-scale platform features.

## Intentionally deferred

The MVP does not require AI grading, handwriting OCR, fully adaptive testing, parent/tutor dashboards, mobile apps, State Boards, JEE, or a large subscription platform.

Expansion to additional subjects should be driven by curriculum validation and real student demand rather than adding subjects only because the technology can support them.
