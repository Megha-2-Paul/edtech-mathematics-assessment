# Question Bank Foundation

The Question Bank is a single unified bank with two supported ingestion paths:

1. `MANUAL` — questions entered by the teacher/admin.
2. `EXTRACTED` — questions produced by the PDF extraction pipeline.

Both paths ultimately produce canonical questions that can be used by the Test Builder. Extracted questions retain provenance and verification history; manual questions do not require a source PDF.

## Core model

- `questions` — canonical reusable question record.
- `question_occurrences` — where a canonical question appeared in a source paper.
- `question_groups` — internal choices, case studies and multi-part contexts.
- `question_parts` — individual parts/alternatives within a group.
- `question_assets` — diagrams, figures, tables, graphs and other visual assets.
- `source_papers` — original PDFs and paper metadata.
- `question_extraction_runs` — each provider/model extraction attempt.
- `question_extraction_results` — candidate outputs and component-level confidence.
- `question_verifications` — human approval/correction/rejection authority.
- `extraction_jobs` — resumable page-level daily queue.
- `extraction_providers` — provider/free-tier checkpoint and quota metadata.
- `extraction_feedback` — structured corrections used to improve prompts, preprocessing and routing.

## Zero-cost rule

The initial extraction workflow must not spend money automatically. A provider is usable only when its current free status has been verified. When free capacity is exhausted, jobs remain queued for a later run. No paid fallback is enabled automatically.

## Verification rule

The source page/image remains the ground truth. Model confidence never replaces human verification for uncertain material.

## Migration

Run `migrations/001_question_bank_foundation.sql` once against the existing `edtech_assessment` MySQL database. The migration is additive and preserves the existing manual question-bank and student-exam tables.
