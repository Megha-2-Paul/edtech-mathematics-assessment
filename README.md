# Mathematics Assessment & Improvement System

A low-cost assessment system for CBSE/ICSE Mathematics that focuses on **why students lose marks and how they improve**, not just scores.

## Canonical product workflow

**Acquire → Register → Assess → Submit → Evaluate → Diagnose → Report → Communicate → Update Student Profile → Recommend Next Focus → Reassess → Measure Improvement**

The complete technical workflow is maintained in:

**[PRODUCT_WORKFLOW.md](PRODUCT_WORKFLOW.md)**

The commercial scope, diagnostic features, pricing hypotheses, marketing funnel and validation gates are maintained in:

**[PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md)**

## Commercial launch scope

### Initial customer-facing product

- **Board:** CBSE
- **Class:** Class 12
- **Subject:** Mathematics
- **Market:** India
- **Product:** Mathematics Diagnostic + Improvement System

The software architecture is **multi-subject-ready**, but the commercial launch is intentionally **single-subject**. Expansion happens only after the Mathematics model is validated.

Planned expansion path:

**CBSE Class 12 Mathematics → CBSE Class 10 Mathematics → CBSE Class 11 Mathematics → ICSE Mathematics → other subjects → tutor/coaching/school infrastructure**

## Product promise

> **Why are you losing marks even when you know the Maths?**

> **Find out exactly where you're losing marks, what to fix next, and whether you're actually improving.**

The test is the input. Diagnosis and measurable improvement are the product value.

## Core improvement loop

```text
Baseline Assessment
      ↓
Evaluation
      ↓
Mark-Loss Map
      ↓
Chapter / Topic / Competency Analysis
      ↓
Knowledge vs Execution Diagnosis
      ↓
Recurring Error Detection
      ↓
Top 3 Improvement Priorities
      ↓
Personalised Next Focus
      ↓
Targeted Practice
      ↓
Next Assessment
      ↓
Test-to-Test Comparison
      ↓
Explain Why Score Changed
      ↓
Measure Improvement
      ↓
Updated Student Profile
      ↓
Repeat
```

## Current repository foundation

- Flask student exam platform
- MCQ + subjective exam workflow
- Handwritten answer uploads
- MySQL/SQLAlchemy persistence layer
- Structured question bank model
- Chapter/topic/competency metadata
- Attempt/response/evaluation data model
- Evaluation error storage
- Student history/improvement data model

## Target MVP

1. Production authentication
2. Professional online Mathematics assessment
3. MCQ + handwritten subjective submission
4. Human evaluation using standard error codes C01–C09
5. Python-based scoring and diagnosis
6. Mark-Loss Map and student-friendly diagnostic report
7. Recurring error and test-to-test improvement analysis
8. Top 3 priorities + rule-based next focus
9. n8n workflow automation
10. WhatsApp + email delivery
11. Longitudinal student profile
12. Second assessment and improvement comparison

## Architecture

```text
Student Website
      ↓
Flask / API
      ↓
MySQL
      ↓
n8n orchestration
      ├── Python analysis
      ├── Report generation
      ├── WhatsApp
      └── Email
      ↓
Student Performance Profile
      ↓
Next Assessment
      ↓
Improvement Measurement
```

## Product principle

> **The product is the Test → Evaluation → Diagnosis → Report → Improvement loop.**

Do not build AI grading, OCR, fully adaptive testing, mobile apps, parent/tutor dashboards, additional subjects, or a large paid advertising system before the core loop is validated with real paying students.

## Validation target

The first major milestone is **20–30 real paying students**.

The most important behavioural metric is:

> **Do students return for Test 2/3 because the diagnosis and improvement tracking are useful?**

Revenue, follower count and number of registered users are secondary to product usefulness and retention during validation.
