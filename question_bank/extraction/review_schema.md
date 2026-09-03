# Extraction → Question Bank Field Contract

The AI extractor and human-review UI must use this contract. The extraction record is deliberately richer than the current `questions` table so source provenance and reusable assets are not lost.

## Canonical question record

Each `questions[]` item should contain:

| Extraction field | Database destination / meaning | Required at approval |
|---|---|---|
| `question_number` | Source-paper question number; provenance, not canonical `question_id` | Yes |
| `question_text` | `questions.question_content_json` text block | Yes |
| `question_parts` | Structured subparts; stored in content/provenance until dedicated normalization | If present in source |
| `answer_choices` | `questions.answer_choices_json` | For MCQ; otherwise `[]` |
| `correct_answer` | `questions.correct_answer` | If known/applicable |
| `marks` | `questions.marks` | Yes |
| `question_type` | `questions.question_type`: `mcq`, `vsaq`, `saq`, `laq` | Yes |
| `answer_mode` | `questions.answer_mode` | Yes |
| `handwritten_upload_mode` | `questions.handwritten_upload_mode` | Yes; normally `none` for question-bank source records |
| `subject` | `questions.subject` | Yes |
| `board` | `questions.board` | Yes |
| `class_level` | `questions.class_level` | Yes |
| `chapter` | `questions.chapter` | Yes/verified before approval |
| `topic` | `questions.topic` | Recommended |
| `subtopic` | `questions.subtopic` | Optional |
| `difficulty` | `questions.difficulty` | Recommended |
| `competency` | `questions.competency` | Recommended |
| `source` / `source_pdf` | `questions.source` plus source-paper provenance | Yes |
| `source_year` | `questions.source_year` | Recommended |
| `diagram_reference` / `assets` | `question_assets` + content image blocks when actual files are available | If source contains visual material |

## Provenance fields (must not be discarded)

The extractor should also return:

- `source_pdf`
- `source_page`
- `source_pages` when a question spans pages
- `source_question_number`
- `source_occurrence_id` if a source-occurrence layer is available
- `extraction_provider`
- `extraction_model`
- `extraction_run_id`
- `extraction_confidence`
- `extraction_warnings`
- `verification_status`
- `verification_note`

These fields are extraction/provenance metadata, not substitutes for the canonical `questions` fields.

## Important rule

Do **not** silently invent chapter, topic, competency, difficulty, correct answer, marks, or question type. If the PDF does not establish a value, the extractor should return `null`/empty and the reviewer should decide it.

Do not confuse the source question number (e.g. `38`) with the canonical database ID (`Q0042`). The canonical ID is generated only when an approved record is inserted into the question bank.

## Current database entities relevant to extraction

The current schema includes `source_papers`, `question_occurrences`, `question_parts`, `question_assets`, `question_history`, `question_verifications`, `extraction_jobs`, `extraction_providers`, `extraction_runs`, `extraction_results`, and `extraction_feedback`, in addition to the canonical `questions` table. The implementation should progressively use these provenance/extraction tables rather than collapsing everything into `questions.question_content_json`.

## Human verification statuses

`PENDING` → reviewer is checking.

`NEEDS_REVIEW` → extraction needs further work; it must not enter the canonical bank automatically.

`REJECTED` → extraction is unusable or not a question to import.

`APPROVED` → reviewer has verified/edited the record and it may enter the canonical question bank.
