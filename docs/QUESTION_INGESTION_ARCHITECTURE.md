# Question Ingestion Architecture

## Purpose

Improvia should be able to accept questions from different source types without coupling the assessment engine to a particular source format.

The architecture therefore separates **source acquisition**, **extraction**, **normalization**, **validation**, **deduplication**, **human review**, and **publication**.

## Pipeline

```text
Source
  ↓
Source Adapter
  ↓
RawQuestion
  ↓
Normalization
  ↓
Deterministic Validation
  ↓
Duplicate Detection
  ↓
Review Queue
  ↓
Human Approval
  ↓
Existing Question model / questions table
  ↓
Test Builder
```

## Supported source contract

The ingestion layer defines these source types:

- `manual`
- `pdf`
- `url`
- `image`
- `api`
- `partner`
- `original`

Stage 1 implemented the manual adapter. Stage 2 adds the PDF adapter. Future adapters must emit the same `RawQuestion` contract rather than writing directly to the production question bank.

## Internal stages

### 1. SourceDocument

Describes the source itself: source ID, type, name, URL/file path, year, rights status, and additional metadata.

### 2. RawQuestion

Represents extractor output before curriculum or production metadata is applied. It may contain raw text, options, answer, marks, assets, source reference, extraction confidence, and extraction metadata.

### 3. NormalizedQuestion

Represents the canonical question structure before publication. It maps to the existing `Question` model rather than creating a second production question schema.

### 4. Validation

Validation checks structural fields that can be evaluated deterministically: required metadata, supported board/type, marks, MCQ options/correct answer, and asset references.

Curriculum validation and answer verification remain human/review responsibilities until dedicated services are introduced.

### 5. Duplicate detection

The pipeline performs deterministic fingerprinting using normalized question text, choices, answer, marks, board, and class. Semantic similarity can be added later without changing the adapter contract.

### 6. Review

A valid candidate is marked `review_required`; it is **not automatically published**. Duplicate and invalid candidates are kept out of the production bank.

## Stage 2 — PDF adapter

`exam_platform/ingestion/adapters/pdf.py` uses **PyMuPDF** to read the PDF text layer and produce `RawQuestion` objects.

The current extractor:

- accepts a local `.pdf` file through `SourceDocument.file_path`
- reads each page independently
- detects common numbered question boundaries such as `1.`, `2)`, `Q3.` and `Question 4:`
- preserves page start/end references
- detects simple `(A) ... (D) ...` / `A. ... D. ...` option lines
- detects simple trailing marks such as `[2 marks]`, `(3 marks)`, or `[1 m]`
- records extraction method and a conservative extraction confidence
- records whether the PDF has a text layer
- flags image-only PDFs as `ocr_required` rather than attempting OCR
- always sends extracted candidates through the existing normalization/validation/review pipeline

This is deliberately a **text-layer extractor, not an OCR or AI parser**. Real mathematics PDFs often contain equations, multi-column layouts, diagrams, tables, headers/footers, and unusual numbering. Those cases must remain reviewable rather than being silently published.

### Example

```python
from exam_platform.ingestion.adapters.pdf import extract_pdf_questions

source, raw_questions = extract_pdf_questions(
    "sample-paper.pdf",
    source_id="CBSE-2026-SAMPLE",
    source_year=2026,
    rights_status="review_required",
)
```

Then feed `raw_questions` to `QuestionIngestionPipeline.prepare(...)` after applying known board/class/chapter metadata. The PDF adapter does not guess curriculum classification.

## MarkItDown extraction layer

MarkItDown is now installed as a **separate document-preprocessing engine** for text-dominant PDFs. The implementation lives in:

```text
question_bank/extraction/
    markitdown_extractor.py
    extraction_router.py
```

The router inspects a PDF before extraction and currently selects:

```text
Text-dominant PDF
    → MarkItDown

Mixed / visually complex PDF
    → existing PyMuPDF/layout extraction

Image-only PDF
    → OCR handoff (future adapter)
```

The MarkItDown adapter returns Markdown/text only. It does **not** replace PyMuPDF page geometry, question cropping, or visual-asset extraction. This is intentional: the original PDF remains the source of truth and the existing visual extraction layer remains responsible for page-level provenance.

The first routing implementation is deliberately conservative. It does not call an LLM, perform OCR, or publish questions automatically.

### Why this is separate

MarkItDown is designed to convert documents into Markdown for text analysis and supports PDF through its optional `pdf` dependency. The application therefore treats it as one extraction engine rather than as the question parser itself.

Question parsing, normalization, validation, duplicate detection, and human approval remain application responsibilities.

### Next integration step

Before replacing the existing PDF parser, benchmark MarkItDown output against the current PyMuPDF extractor on representative CBSE/ICSE mathematics PDFs. The benchmark should compare:

- question boundary preservation
- mathematical text preservation
- MCQ option preservation
- marks preservation
- headers/footers
- multi-column ordering
- tables
- diagrams/assets
- page provenance

Only after that benchmark should MarkItDown become the primary text source for the relevant PDF route.

## Assets

Stage 2 records page provenance and exposes the `raw_assets` channel for future PDF asset extraction. It does **not** commit extracted binary images into the repository and does not attempt OCR of image-only pages.

This keeps the repository clean and allows a later storage layer to place question diagrams/images in object storage or the existing `question_assets` workflow after human review.

## Scanned PDFs

If a PDF has no usable text layer, the adapter returns no questions and sets `SourceDocument.metadata["ocr_required"] = True`. This is intentional. OCR should be a separate adapter/service so that OCR uncertainty can be measured independently from normal PDF text extraction.

## Publication boundary

The existing `questions` table remains the production question bank. Existing persistence through `storage.create_question()` and question assets should be reused when a reviewed candidate is explicitly approved.

The ingestion pipeline intentionally does not auto-insert candidates into the production table.

## Provenance

Every candidate should retain enough provenance to answer:

- Where did this question originate?
- Which source/page/reference produced it?
- Which extraction method was used?
- What year/source version was involved?
- What is the rights/licensing status?

Stage 1 keeps provenance as an ingestion-layer object. A persistent `question_sources` table can be introduced when source history needs to survive independently of the question record.

## Curriculum architecture

Curriculum data is independent from source adapters. A PDF parser should never decide what a chapter means. Instead, normalized questions are mapped against the board/class curriculum.

CBSE and ICSE curriculum records must not share the same chapter seed. ICSE Class 10 is based on the CISCE syllabus; Classes XI-XII are formally ISC rather than ICSE and should be represented separately when higher-secondary curriculum data is introduced.

Official curriculum sources should be used when curriculum data is refreshed.

## Future adapters

Future implementation can add:

```text
exam_platform/ingestion/adapters/
    url.py
    image.py
    api.py
    partner.py
```

None of these adapters should need to modify the evaluation, diagnosis, reporting, student-profile, or test-attempt systems.

## Stage boundaries

### Stage 1

- ingestion contracts
- manual adapter
- deterministic validation
- provenance representation
- deterministic duplicate detection
- review-state model
- curriculum seed separation
- architecture documentation

### Stage 2

- text-layer PDF ingestion
- numbered question extraction
- simple MCQ option extraction
- simple marks extraction
- page-level provenance
- scanned-PDF detection / OCR handoff flag
- ingestion pipeline integration tests

### Stage 2.1 — MarkItDown preprocessing

- MarkItDown PDF dependency
- isolated MarkItDown PDF extractor
- PDF inspection/routing layer
- text-dominant PDF routing to MarkItDown
- tests for text-based and image-only routing
- benchmark before replacing the existing PyMuPDF question parser

### Stage 3

- URL/HTML ingestion
- image/OCR ingestion
- improved duplicate detection
- richer PDF layout handling and diagram extraction

### Future

- AI-assisted metadata classification
- answer verification assistance
- semantic duplicate detection
- confidence-based review routing
- LLM/Vision fallback for extraction cases that deterministic engines cannot reliably parse

AI must assist the review process rather than silently publish unverified questions.
