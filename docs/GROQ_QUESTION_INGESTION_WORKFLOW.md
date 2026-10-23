# Future Workflow — Groq-Assisted Question Ingestion

## Status
**Planned / Deferred.** Documented now; implementation starts only after the current curriculum/database migration is completed and verified.

## Goal
Enrich the Improvia question bank from legitimate PDFs, URLs, images, and documents while preserving the existing ingestion, taxonomy, review, provenance, duplicate-detection, publication, and cloud-sync boundaries.

## Architecture
Source → acquisition → PDF/HTML/image preprocessing → question boundary detection/chunking → Groq extraction → strict JSON extraction contract → existing AIJSONQuestionExtractor → normalization → canonical taxonomy → deterministic validation → duplicate detection → human review → rights/source verification → canonical Question model → question-bank sync.

**Groq is an extraction provider, not the owner of the question bank.**

## Core principles
1. Source fidelity over raw question volume.
2. Extract only questions that actually exist in the source; never invent missing text, marks, options, diagrams, answers, or questions.
3. AI output is untrusted until human review.
4. Reuse the existing AI JSON extraction contract and ingestion pipeline instead of creating a second production schema.
5. Preserve source, page, question number, provider, model, run ID, timestamp, warnings, confidence, and rights/licensing provenance.
6. Keep extraction separate from curriculum classification.
7. Never allow an AI response to directly publish into the production question bank.

## Provider architecture
Use a replaceable provider layer. Groq should be one provider alongside possible future OpenAI, Gemini, or other providers. All providers should emit the same Improvia extraction contract.

Proposed future modules:
- question_bank/providers/groq_provider.py
- question_bank/extraction/groq_extractor.py
- question_bank/extraction/source_downloader.py
- question_bank/extraction/pdf_chunker.py

Do not couple the production Question model directly to Groq.

## PDF workflow
1. Acquire and preserve the source.
2. Inspect the PDF with deterministic tooling first, including the existing PyMuPDF/layout components.
3. Route text-dominant PDFs to text extraction; mixed/visually complex PDFs to text plus geometry/assets; scanned/image-only PDFs to a future OCR/vision route.
4. Reuse the existing question-boundary and cropping infrastructure where possible.
5. Send page/question chunks to Groq rather than unnecessarily sending an entire large paper in one request.
6. Preserve page and source references for every extracted question.

## Groq extraction
Groq should return strict JSON matching the existing extraction contract. It should preserve question numbering, subquestions, options, marks, mathematical meaning, diagrams/tables/graphs as assets or references, and uncertainty warnings.

It must not silently repair or invent source content.

Expected fields include question_number, question_text, question_parts, answer_choices, correct_answer, marks, question_type, answer_mode, handwritten_upload_mode, subject, board, class_level, chapter, topic, subtopic, difficulty, competency, source_page, source_pages, source_question_number, diagram_reference, assets, extraction_confidence, extraction_warnings, and provider/model/run provenance.

## Two-pass AI design
Prefer two logically separate passes.

### Pass 1 — Extraction
Answer: What questions are actually present? Extract text, parts, options, marks, source/page references, assets, and optional unverified answers.

### Pass 2 — Classification
Answer: Which canonical chapter/topic/difficulty/competency does this question belong to? Give the classifier the existing board/class taxonomy and require canonical values rather than arbitrary chapter names.

Example: an AI label such as 'Quadratic Equation' should be resolved to the canonical taxonomy value 'Quadratic Equations'.

## Vision and mathematical documents
Maths PDFs can contain diagrams, graphs, tables, geometry figures, and equation formatting that plain text extraction loses. A future vision route should provide the question crop plus visual asset to a vision-capable model and retain the original page as the source of truth.

## URL workflow
URL → fetch source → identify PDF/HTML/image → route to the appropriate deterministic extractor → same JSON contract → same review pipeline.

Do not rely on LLM web browsing as the primary source-acquisition mechanism. Deterministic retrieval is preferred so the exact source can be preserved and reproduced.

## Validation
After Groq extraction, pass the response through AIJSONQuestionExtractor and the existing ingestion pipeline.

Validate required text, supported question type, marks, MCQ option structure, MCQ answer validity, source/page references, board/class values, assets, and schema version.

A syntactically valid JSON response is not a verified mathematics question.

## Taxonomy
Never allow Groq to introduce production chapter names directly. Use the existing CanonicalTaxonomyResolver. If classification cannot be resolved confidently, keep the candidate pending for human review.

## Duplicate detection
Bulk ingestion will create major duplicate risk across board papers, sample papers, question banks, coaching material, and websites.

Use deterministic normalized fingerprints first. Later, add semantic similarity for potential duplicates followed by human review. Similar questions such as 'Find the roots of x² - 5x + 6 = 0' and 'Find the zeroes of x² − 5x + 6' should not automatically become separate canonical questions.

## Publication boundary
Extracted → validated candidate → PENDING → human review → rights confirmed → canonical Question → active/reusable.

No Groq response should directly insert into the production question bank.

## Batch ingestion
Once single-source extraction is reliable, support large batches using resumable/idempotent jobs. A future batch API can process many question chunks efficiently, but every result must still pass validation, duplicate detection, review, and rights checks.

## Benchmark before scaling
Before processing hundreds of sources, benchmark representative CBSE/ICSE Mathematics PDFs.

Measure: question boundary accuracy; question text accuracy; mathematical notation preservation; subquestion preservation; MCQ option accuracy; marks accuracy; answer extraction accuracy; page provenance; diagram/graph/table preservation; chapter classification accuracy; duplicate detection quality; cost per usable question; processing time; human review time.

Choose a model/provider based on verified usable questions per unit of cost and review effort, not raw extraction count or speed.

## Rights and security
Only ingest sources that Improvia is permitted to process and use. A publicly accessible URL is not automatically a redistribution right.

Store GROQ_API_KEY only in environment variables or a secure secret store. Never commit it, include it in generated JSON, expose it in the review UI, or print it in logs.

## Deferred implementation plan
### G0 — Documentation
- This architecture
- Provider contract
- Extraction prompt specification
- Benchmark criteria

### G1 — Single PDF proof of concept
- Groq provider
- strict JSON output
- one local PDF
- saved raw response
- conversion through existing AIJSONQuestionExtractor
- no automatic publication

### G2 — Review integration
- extraction batch record
- review queue integration
- taxonomy resolver integration
- provenance display
- validation/error reporting

### G3 — URL and visual sources
- URL/PDF downloader
- HTML extraction
- scanned PDF/vision route
- image/diagram handling

### G4 — Bulk enrichment
- batch processing
- resumable jobs
- run IDs
- duplicate detection
- benchmark reporting
- cost/throughput monitoring

### G5 — Production hardening
- provider abstraction
- retry/backoff
- rate-limit handling
- failure recovery
- audit logs
- rights checks
- monitoring

## First implementation target
After migration completion, start with one local PDF and a CLI such as:

python -m question_bank.ingest_groq pdf sample-paper.pdf

Expected result: PDF → Groq extraction → strict JSON → AIJSONQuestionExtractor → validated candidates → reviewable output.

Only after this is reliable should URL ingestion and large-scale bulk enrichment be added.

## Non-goals
- Automatically publish AI-extracted questions.
- Automatically verify mathematics answers.
- Replace the existing taxonomy.
- Replace the current question-bank schema.
- Replace human review.
- Build a student-facing AI feature.
- Generate new questions from scratch.
- Process arbitrary internet content without source/rights checks.

The immediate objective is reliable, traceable source-question extraction to enrich the Improvia question bank.