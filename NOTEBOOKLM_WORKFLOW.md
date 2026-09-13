# NotebookLM Workflow

## Purpose

NotebookLM is a **supporting research and knowledge tool** for the Mathematics Assessment & Improvement System. It is not the assessment engine, database, grading engine, analytics engine, or student exam platform.

The purpose is to reduce founder research time and improve the quality and consistency of CBSE/ICSE assessment design and supporting content.

## Where NotebookLM fits

```text
                    SOURCE / KNOWLEDGE LAYER

 CBSE official material / licensed content / own material
                         |
                         v
                  +--------------+
                  |  NotebookLM  |
                  | Research +   |
                  | source-ground |
                  |   analysis    |
                  +------+-------+
                         |
                         v
                Validated decisions
                         |
                         v
                  Question Bank /
                Assessment Design / Content
                         |
                         v
                    CORE PLATFORM
                         |
                         v
 Student -> Exam -> Submission -> Human Evaluation
                         |
                         v
                 MySQL -> Python Analytics
                         |
                         v
                 Diagnosis -> Report ->
                 Profile -> Next Test
```

## Primary uses

### 1. CBSE/ICSE curriculum research

Use NotebookLM to work with authoritative or permitted source material such as:

- Official board syllabus/curriculum documents
- Official sample papers
- Official marking schemes
- Official circulars/instructions
- NCERT material where use is permitted
- Content created or licensed by the business

Questions can include:

- What topics and competencies are covered?
- What assessment requirements are stated?
- What marking points appear in official material?
- What changes between assessment cycles?
- Which source supports a particular interpretation?

### 2. Question-bank development

NotebookLM can help investigate a source set before questions are added to the structured question bank.

Suggested analysis dimensions:

- Chapter
- Topic/subtopic
- Question type
- Marks
- Difficulty
- Competency
- Concept tested
- Expected solution approach
- Common misconception or error pattern
- Source/year

NotebookLM output is **research input**, not an automatic approval mechanism. Final questions must be mathematically and pedagogically validated before entering the production question bank.

### 3. Marking-scheme and evaluation research

Use source-grounded analysis to understand how marks are allocated and what solution steps/justifications matter.

This informs the business's structured evaluation framework, including the initial error taxonomy:

- C01 — Calculation
- C02 — Conceptual
- C03 — Formula
- C04 — Sign
- C05 — Incomplete steps
- C06 — Wrong method
- C07 — Missing justification
- C08 — Misunderstood question
- C09 — Time/attempt

NotebookLM does **not** assign official marks to student submissions.

### 4. Content research and validation

Use it to research and cross-check educational content for:

- Instagram/YouTube ideas
- Lost-mark examples
- Exam strategy content
- Marking/presentation explanations
- Chapter-specific guidance
- FAQ material

Claims should be checked against authoritative sources before publication.

### 5. Internal learning/research

The founder can use notebooks as persistent knowledge bases for topics such as:

- CBSE Class 12 Mathematics
- CBSE Class 10 Mathematics
- ICSE Mathematics
- Assessment design
- Marking schemes
- Question quality
- Common student mistakes

## What NotebookLM must NOT own

Do not make NotebookLM responsible for:

- Student authentication
- Exam UI
- Exam timing
- Submission handling
- Persistent student records
- Question-bank production database
- Final mathematical scoring
- Subjective grading
- Error-code storage
- Longitudinal analytics
- Diagnosis rules
- Personalisation logic
- Secure report generation
- Payment processing
- WhatsApp/email orchestration

The source of truth remains the platform's database and structured application logic.

## Relationship to the existing architecture

### NotebookLM

Research, source comparison, knowledge synthesis and content development.

### Flask / API

Student-facing platform, authentication, exam/session logic and APIs.

### MySQL

Persistent source of truth.

### Human evaluator

Initial subjective grading and structured error coding.

### Python

Scoring, analytics, longitudinal comparison, diagnosis and recommendations.

### n8n

Workflow orchestration and communication.

### Report generator

Student-facing PDF/HTML reports.

## Recommended operating procedure

1. Collect authoritative/permitted sources.
2. Organise them into a NotebookLM notebook by subject/board/class or research purpose.
3. Ask source-grounded questions to identify requirements, patterns and gaps.
4. Record important conclusions and source references.
5. Independently verify high-impact mathematical/assessment decisions.
6. Convert validated information into structured question-bank or product data.
7. Keep NotebookLM as the research layer rather than the production database.

## Suggested initial notebooks

```text
01 — CBSE Class 12 Mathematics — Official Sources
02 — CBSE Class 10 Mathematics — Official Sources
03 — ICSE Mathematics — Official Sources
04 — Question Bank Research — PYQs / Samples / Marking
05 — Assessment & Marking Research
06 — Marketing Content Research
```

Create notebooks only when they have a clear research purpose. Avoid collecting large amounts of material without a defined use.

## Free/paid policy for MVP

Start with the available free/standard NotebookLM access. Do **not** make a paid NotebookLM subscription a prerequisite for MVP launch.

Usage limits, supported features and plan limits can change. Re-check Google's current documentation before depending on a specific limit or paid feature.

## Copyright and source-use rule

Only upload material that the business/user has the right to use. Prefer official public sources, properly licensed material, and original business content. Do not treat technical ability to upload a document as permission to reproduce or commercially use it.

## AI policy

NotebookLM is an AI assistant and can make mistakes. Source grounding reduces unsupported answers but does not eliminate the need for human verification.

For Mathematics Assessment:

> **AI assists research; humans validate assessment decisions.**

This is consistent with the MVP principle of proving customer value before investing in AI grading or automated handwriting understanding.

## Roadmap placement

### V1 — Current validation stage

Use NotebookLM manually for:

- CBSE/ICSE research
- syllabus and marking-scheme research
- question-bank research
- assessment/content validation

No API integration is required.

### V2 — Operational improvement

Continue using NotebookLM for structured research and content development. Standardise notebooks, prompts and internal research outputs.

### V3+

Only investigate deeper AI/knowledge integrations if there is a demonstrated business need. Do not build a custom NotebookLM integration merely because it is technically possible.

## Core principle

NotebookLM should make **building and researching the assessment system faster and better**. It should not become another layer that makes the production system harder to operate.
