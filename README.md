# Mathematics Assessment & Improvement System

A low-cost assessment system for CBSE/ICSE Mathematics that focuses on **why students lose marks and how they improve**, not just scores.

## Canonical product workflow

**Acquire → Register → Assess → Submit → Evaluate → Diagnose → Report → Communicate → Update Student Profile → Recommend Next Focus → Reassess → Measure Improvement**

The complete architecture and implementation workflow is maintained in:

**[PRODUCT_WORKFLOW.md](PRODUCT_WORKFLOW.md)**

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

1. Student registration/authentication
2. Professional online Mathematics assessment
3. MCQ + handwritten subjective submission
4. Human evaluation using standard error codes C01–C09
5. Python-based scoring and diagnosis
6. Individual PDF performance report
7. n8n workflow automation
8. WhatsApp + email delivery
9. Longitudinal student profile
10. Next-focus recommendation
11. Second assessment and improvement comparison

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
```

## Product principle

> **The product is the Test → Evaluation → Diagnosis → Report → Improvement loop.**

Do not build AI grading, adaptive testing, parent/tutor dashboards, mobile apps, or additional subjects before the core loop is validated with real paying students.

## Development status

The repository currently contains a working student exam-platform MVP plus the MySQL persistence foundation. The next major milestone is to connect production authentication, evaluation, analytics, reporting and workflow automation into one complete commercial assessment cycle.
