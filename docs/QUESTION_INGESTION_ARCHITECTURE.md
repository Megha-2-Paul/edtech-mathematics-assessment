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

The ingestion layer currently defines these source types:

- `manual`
- `pdf`
- `url`
- `image`
- `api`
- `partner`
- `original`

Only the manual adapter is implemented in Stage 1. Future adapters must emit the same `RawQuestion` contract rather than writing directly to the production question bank.

## Internal stages

### 1. SourceDocument

Describes the source itself: source ID, type, name, URL/file path, year, rights status, and additional metadata.

### 2. RawQuestion

Represents extractor output before curriculum or production metadata is applied. It may contain raw text, options, answer, marks, assets, source reference, and extraction confidence.

### 3. NormalizedQuestion

Represents the canonical question structure before publication. It maps to the existing `Question` model rather than creating a second production question schema.

### 4. Validation

Validation checks structural fields that can be evaluated deterministically: required metadata, supported board/type, marks, MCQ options/correct answer, and asset references.

Curriculum validation and answer verification remain human/review responsibilities until dedicated services are introduced.

### 5. Duplicate detection

Stage 1 performs deterministic fingerprinting using normalized question text, choices, answer, marks, board, and class. Semantic similarity can be added later without changing the adapter contract.

### 6. Review

A valid candidate is marked `review_required`; it is **not automatically published**. Duplicate and invalid candidates are kept out of the production bank.

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
    pdf.py
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

- PDF ingestion
- question extraction
- asset extraction
- candidate review workflow

### Stage 3

- URL/HTML ingestion
- image/OCR ingestion
- improved duplicate detection

### Future

- AI-assisted metadata classification
- answer verification assistance
- semantic duplicate detection
- confidence-based review routing

AI must assist the review process rather than silently publish unverified questions.
