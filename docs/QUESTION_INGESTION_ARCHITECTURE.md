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

Stage 1 implemented the manual adapter. Stage 2 adds the PDF adapter. Stage 3A adds the URL adapter. Future adapters must emit the same `RawQuestion` contract rather than writing directly to the production question bank.

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

## Stage 3A — URL/HTML adapter

`exam_platform/ingestion/adapters/url.py` adds a standard-library URL adapter for public HTTP(S) HTML pages.

The adapter:

- validates the URL scheme before fetching
- uses a bounded HTTP request with a short timeout and response-size limit
- parses visible HTML text while ignoring script/style/SVG content
- detects common numbered question boundaries
- extracts simple A-D option lines and trailing marks
- preserves a source URL reference and extraction metadata
- records chapter/topic text as a **hint only**; it does not automatically assign production curriculum metadata
- returns `RawQuestion` candidates with conservative extraction confidence
- always marks URL-derived questions as requiring human review

This stage is intentionally a **candidate extractor**, not a web crawler. It does not follow every link, paginate through thousands of results, bypass access controls, download arbitrary assets, or publish scraped content.

### Shaalaa pilot

The first real-world extraction target is the ICSE Class 10 Mathematics question-bank URL supplied during development. The intended pilot is approximately **20–30 candidates**, not the full question-bank corpus.

The extracted candidates should be reviewed for:

- question boundary accuracy
- mathematical text/equation integrity
- option and marks extraction
- chapter/topic hints
- duplicate rate
- answer availability and correctness
- syllabus/currentness
- diagram/image loss
- extraction confidence
- licensing/commercial-use status

External-source extraction is a research/review workflow unless the source's rights permit reuse. A candidate is therefore not production-ready merely because the parser extracted it successfully.

### Example

```python
from exam_platform.ingestion.adapters.url import extract_url_questions

source, raw_questions = extract_url_questions(
    "https://example.com/question-bank",
    source_id="URL-PILOT-001",
    source_year=2026,
    rights_status="unknown",
    metadata={"board": "ICSE", "class_level": 10},
)
```

Then pass the candidates through `QuestionIngestionPipeline.prepare(...)`. Do not insert the raw output directly into `questions`.

## Assets

Stage 2 records page provenance and exposes the `raw_assets` channel for future PDF asset extraction. It does **not** commit extracted binary images into the repository and does not attempt OCR of image-only pages.

Stage 3A similarly does not download arbitrary URL images into the production asset store. Image/OCR handling remains a separate stage so mathematical diagrams can be reviewed explicitly.

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

Curriculum data is independent from source adapters. A PDF or URL parser should never decide what a chapter means. Instead, normalized questions are mapped against the board/class curriculum.

CBSE and ICSE curriculum records must not share the same chapter seed. ICSE Class 10 is based on the CISCE syllabus; Classes XI-XII are formally ISC rather than ICSE and should be represented separately when higher-secondary curriculum data is introduced.

Official curriculum sources should be used when curriculum data is refreshed.

## Future adapters

Future implementation can add:

```text
exam_platform/ingestion/adapters/
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

### Stage 3A

- bounded URL/HTML fetching
- visible-text extraction
- numbered question candidate extraction
- simple MCQ option/marks extraction
- source URL provenance
- chapter/topic hints as non-authoritative metadata
- explicit human-review boundary
- fixture-based extraction tests
- no automatic production publishing

### Future Stage 3B

- source-specific parsers where generic HTML extraction is insufficient
- image/OCR ingestion
- improved duplicate detection
- richer PDF layout handling and diagram extraction
- persistent ingestion/review queue

### Future

- AI-assisted metadata classification
- answer verification assistance
- semantic duplicate detection
- confidence-based review routing

AI must assist the review process rather than silently publish unverified questions.
