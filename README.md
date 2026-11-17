# Improvia — Mathematics Assessment & Improvement System

Improvia helps students understand **where they lose marks, why they lose them, what to practise next, and whether they improve**.

It is a diagnostic assessment and improvement system, not simply a mock-test website.

**Core loop:** Registration → Eligibility → Assessment → Submission → Human evaluation → Diagnosis → Report → Practice → Reassessment → Progress comparison.

## Approved initial product focus

- CBSE and ICSE Mathematics.
- Classes 10–12.
- Controlled, founder-operated validation before broader commercial launch.

Curriculum structures or question-bank data for other classes, boards or subjects are technical capabilities, not approval to include them in the launch. Any expansion needs a separate product-scope decision.

## Product principles

- Handwritten Mathematics answers are marked by a human.
- Do not use unsupervised AI grading.
- Explain marks lost with evidence and plain-language feedback.
- Preserve the C01–C09 Mathematics error taxonomy unless a reviewed change is approved.
- An unanswered question alone does not prove a conceptual weakness.
- Measure improvement across distinct assessments rather than relying on one score.

## Current development approach

Development and end-to-end verification are local-first. Continue using an isolated local MySQL database and synthetic data. Hosting, production database and scale-out decisions are deferred until the core workflow is complete, measured and verified.

A feature existing in code, a passing CI run, local end-to-end verification and production readiness are different evidence levels. Do not treat them as interchangeable.

## Start here

- [Documentation index](docs/README.md) — authoritative document map and status.
- [Canonical product workflow](docs/product/PRODUCT_WORKFLOW.md).
- [Platform verification and release readiness](docs/engineering/PLATFORM_VERIFICATION.md).
- [Current repository development audit](docs/engineering/DEVELOPMENT_AUDIT.md).
- [Local development quick start](docs/operations/QUICK_START.md).
- [Architecture reference](docs/architecture/PRODUCTION_ARCHITECTURE.md).
- [Repository instructions](docs/CHATGPT_INSTRUCTIONS.md).

## Mathematics error taxonomy

| Code | Category |
|---|---|
| C01 | Calculation |
| C02 | Conceptual |
| C03 | Formula |
| C04 | Sign |
| C05 | Incomplete steps |
| C06 | Wrong method |
| C07 | Missing justification |
| C08 | Misunderstood question |
| C09 | Time/attempt |

Use codes only when supported by marking evidence. Other subjects, if separately approved later, need appropriate subject-specific diagnosis.

## Technology

Python, Flask, Jinja2, SQLAlchemy and MySQL. Inspect the documentation index for architecture, database, security, deployment, question-bank, testing and operating references.

## Safety and privacy

Students may be minors. Treat names, contacts, handwritten work, submissions, marks, reports and performance history as private. Use synthetic data for development and testing. Never commit secrets, student records, uploads or database dumps. Never run unapproved production migrations or destructive operations.

## Development workflow

Read [docs/CHATGPT_INSTRUCTIONS.md](docs/CHATGPT_INSTRUCTIONS.md) and [AGENTS.md](AGENTS.md) before repository work. Inspect code, tests, migrations, branches and PR dependencies; prepare a plan and wait for approval before changes. The owner reviews and tests locally.
