# AI extraction contract

The provider layer should produce one JSON batch per source and place it in the extraction inbox. The canonical schema version is **1.0**.

The human-review interface reads this contract and **does not import anything into the canonical question bank automatically**.

## Canonical question fields

Each question is normalized to:

- question_number — source numbering only; never the canonical database ID.
- question_text
- question_parts
- answer_choices
- correct_answer
- marks
- question_type — mcq, vsaq, saq, or laq
- answer_mode
- handwritten_upload_mode — none, optional, or required
- subject, board, class_level
- chapter, topic, subtopic
- difficulty, competency
- provenance fields such as source_page, source_pages, source_question_number, diagram_reference, and assets.

## Supported provider aliases

Providers may use these aliases; the extractor normalizes them:

| Canonical | Accepted aliases |
|---|---|
| question_text | text, question |
| question_type | type |
| answer_choices | options |
| class_level | class |
| question_parts | parts, subquestions |
| source_page | page_number, page |
| source_pages | pages |
| source_file | source_pdf, file_path, file |
| extraction_provider | provider |
| extraction_model | model |
| extraction_run_id | run_id |

The normalized internal representation uses the canonical names only.

## Source/provenance

source may be a structured object or a legacy string accompanied by source_details. Source file, year, label, provider, model, and run ID are retained as provenance.

## Rules

1. Preserve mathematical notation as faithfully as possible.
2. Do not invent missing text, marks, options, diagrams or answers.
3. Keep subquestions grouped under their parent question.
4. Record the source page for every question when known.
5. Diagrams, tables and graphs must be referenced rather than silently discarded.
6. Classification fields may be null during extraction.
7. correct_answer is untrusted until human verification.
8. Every extracted question remains PENDING until the review gate.
9. Raw provider output is retained separately from the normalized candidate.
10. A valid JSON payload is **not** equivalent to a verified mathematics question.

The JSON schema is stored in question_bank/extraction/question_bank_extraction.schema.json.
