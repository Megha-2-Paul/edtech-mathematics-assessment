# Extraction Implementation Audit & Current Status

Audit date: 2026-09-26
Audited base: master at 5df5bc30a6f55df9aa0a32e68819816850a8191e

## Executive summary

The extraction system is substantially built. It now has source-agnostic ingestion contracts, PDF extraction, MarkItDown preprocessing, external-AI JSON ingestion, normalization, deterministic validation, duplicate detection, provenance, persistent review state, human review, visual inspection, canonical question publishing, solution persistence, and the canonical Mathematics taxonomy.

The core rule is correct: extraction is not verification. Imported questions must remain reviewable until a human verifies them.

The main architectural issue is that two generations of review logic coexist: the newer exam_platform.ingestion pipeline and the older question_bank/extraction/review_app.py flow. The AI JSON approval path has been routed through the newer pipeline, but parts of the legacy path still construct canonical questions directly. These should eventually converge on one approval/publication path.

## What is already built

- Source-agnostic contracts: SourceDocument, RawQuestion, NormalizedQuestion, ValidationResult, IngestionCandidate and IngestionStatus.
- PDF text-layer extraction using PyMuPDF, with question boundaries, simple MCQ options, marks, page provenance and OCR-required detection.
- MarkItDown as a separate PDF document-preprocessing engine; benchmarking is still required before replacing the existing PyMuPDF parser.
- External-AI JSON bulk import through AIJSONQuestionExtractor and AIJSONBulkImporter.
- Deterministic validation for required metadata, question type, marks, MCQs, upload mode, difficulty labels and basic assets.
- Deterministic duplicate fingerprinting using normalized text, choices, answer, marks, board and class.
- Persistent extraction review batches/items and human review UI.
- Source PDF page rendering, question cropping, visual inspection and question asset persistence.
- Explicit rights/licensing confirmation for the newer AI JSON approval path.
- Canonical Question building and question_solutions persistence.
- Canonical Mathematics taxonomy version 2026.27.4: 2 subjects, 88 canonical chapters, 62 syllabus units and 133 syllabus mappings.

## Important findings

### 1. AI JSON source/provenance compatibility bug

The current AI JSON adapter accepts structured source objects, but a question record containing a string source label together with source_details can be rejected because the string source is selected before source_details. The adapter should support both forms and preserve all provenance.

### 2. Top-level source metadata needs the same normalization

Source label, source file/document, year, rights status, provider, model and extraction run should be normalized once at the adapter boundary.

### 3. Two review-state vocabularies coexist

The newer ingestion model uses EXTRACTED, NORMALIZED, VALIDATION_PENDING, REVIEW_REQUIRED, APPROVED, REJECTED, DUPLICATE and OUTDATED. The older UI also uses PENDING and NEEDS_REVIEW. These should eventually be unified.

### 4. Legacy approval can bypass the newer pipeline

The older review application contains a direct conversion path from extraction data to a canonical Question. The target architecture is for PDF, AI JSON, manual and future URL/image sources to converge on one RawQuestion -> NormalizedQuestion -> Validation -> Duplicate detection -> Review -> Approval -> Canonical Question path.

### 5. VERIFIED must remain an approval outcome

The canonical builder currently defaults verification_status to VERIFIED. That is safe only at an explicit approved publication boundary. Unreviewed candidates must never reach that builder as production questions.

### 6. Validation is structural, not mathematical

Current validation can detect malformed metadata, missing fields and MCQ structural problems. It cannot establish mathematical correctness, diagram interpretation, graph transcription, source-answer correctness or academic chapter correctness. Those remain human-review responsibilities.

### 7. Canonical taxonomy is not yet deeply integrated into extraction

The taxonomy exists, but extracted chapter values are still largely treated as supplied metadata. The next version should resolve AI labels against canonical chapter names/IDs and flag uncertain mappings for review instead of inventing new chapter names.

### 8. Visual handling needs explicit status

The review system already supports page renders, question crops and stored visual assets. The next validation layer should distinguish no visual required, visual captured, visual missing, graph/diagram required and visual extraction uncertain.

## Target extraction state model

RAW -> NORMALIZED -> VALIDATED -> REVIEW_REQUIRED -> APPROVED -> PUBLISHED

Rejection, duplicate status, extraction confidence, curriculum confidence, answer-verification status, visual status and rights status should remain separate signals rather than being collapsed into one field.

## Next extraction implementation phase

1. Fix AI JSON source/provenance normalization.
2. Define a strict canonical JSON contract with backward-compatible aliases.
3. Integrate canonical taxonomy resolution.
4. Expand deterministic validation.
5. Add explicit review flags such as ANSWER_UNVERIFIED, CHAPTER_UNCERTAIN, SYLLABUS_UNCERTAIN, DIAGRAM_REQUIRED, GRAPH_REQUIRED, IMAGE_MISSING, SOURCE_DISCREPANCY, INTERNAL_CONTRADICTION and LOW_EXTRACTION_CONFIDENCE.
6. Unify review-state vocabulary.
7. Route every approval through one publication service.
8. Add comprehensive extraction tests using realistic CBSE/ICSE Mathematics payloads.
9. Re-run the existing 51-question JSON batch through the hardened pipeline.
10. Only after this foundation is reliable should AI-assisted answer verification or more advanced extraction be added.

## Current product status

Registration MVP: complete and tested end-to-end through Google Form -> Sheet -> Apps Script -> Render -> Aiven. Browser authentication/access is a separate feature.

Question-ingestion foundation: implemented.
PDF extraction: implemented.
MarkItDown preprocessing: implemented as a separate engine.
External AI JSON: implemented but needs hardening.
Human review: functional MVP.
Canonical Mathematics taxonomy: implemented.

## Decision

The next extraction milestone is not more extraction features. It is making the existing pipeline trustworthy: preserve provenance, enforce canonical taxonomy, detect structural/content risks, require human verification, and use one publication boundary.

For Improvia, a smaller number of correctly verified questions is more valuable than a large automatically imported question bank.