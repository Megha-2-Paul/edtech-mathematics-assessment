# Bulk AI JSON Question-Bank Workflow

## Purpose

Improvia uses external AI only as an extraction assistant. The canonical question bank is populated through a repeatable review-first pipeline:

PDF -> Claude/Gemini -> JSON -> upload -> deterministic normalization -> taxonomy resolution -> validation -> duplicate detection -> persistent review queue -> human approval -> canonical question bank

Nothing from an external AI JSON file is published automatically.

## 1. Prepare the source PDF

Use a stable filename such as:

`ICSE_Class10_Mathematics_2026-27_Sample_01.pdf`

Keep the original PDF unchanged. Record the board, class, subject and academic year from the source itself. If any of these are unclear, leave the corresponding JSON value null and review it later.

## 2. Generate JSON with Claude or Gemini

Upload the PDF and use the extraction prompt below. The prompt is intentionally strict: extract; do not teach, solve, rewrite, or invent.

### Master extraction prompt

```text
You are an exam-question extraction engine for Improvia, a Mathematics Assessment & Improvement System.

Your task is to extract every distinct mathematics question from the attached PDF into ONE valid JSON object.

IMPORTANT RULES
1. Extract only what is present in the PDF. Do not invent, repair, solve, or improve a question.
2. Preserve mathematical notation, symbols, equations, fractions, powers, roots, coordinates, units, and wording as faithfully as possible.
3. Preserve question numbering and sub-question/part structure.
4. Record the PDF page number(s) where the question appears.
5. If a question depends on a diagram, graph, table, construction, or image, explicitly record that dependency. Do not invent missing visual information.
6. If the PDF does not explicitly establish a field, use null rather than guessing.
7. correct_answer is untrusted extraction data. Copy an answer only when it is explicitly present in the source or supplied solution. Do not calculate an answer merely to fill the field.
8. Do not mark any question VERIFIED. All extracted questions must have verification_status = PENDING.
9. Use the canonical subject, board and class values supplied below.
10. For chapter, use ONLY an exact canonical chapter name from the supplied taxonomy. If the source label cannot be mapped confidently to one exact canonical chapter, set chapter to null and add an extraction warning.
11. Do not create chapter names such as 'Algebra - Quadratic Equations' or 'Geometry/Mensuration'. Use the exact canonical chapter name only.
12. topic and subtopic may preserve source terminology when useful, but must not be used to invent a chapter.
13. Difficulty must be one of Easy, Moderate, Difficult when it is explicitly supported. Otherwise use null.
14. competency should be used only when supported by the source/question design; otherwise use null.
15. Return JSON only. No markdown fences. No commentary before or after the JSON.
16. JSON escaping is mandatory. Mathematical notation may contain backslashes; inside JSON strings every literal backslash must be escaped. For example, a LaTeX command such as `\\theta` must be represented as `\\\\theta` in the raw JSON file.
17. Before returning the final answer, validate that the complete output is syntactically valid JSON. Do not return pseudo-JSON, a Python dictionary, or Markdown containing JSON.

CANONICAL SCOPE
subject: Mathematics
board: {{BOARD}}
class_level: {{CLASS}}
academic_year: {{ACADEMIC_YEAR}}

CANONICAL CHAPTER TAXONOMY
Use the attached/provided canonical_math_taxonomy_2026_27.json as the single source of truth.
Only exact chapter names from that taxonomy may be emitted.

OUTPUT CONTRACT
{
  "schema_version": "1.0",
  "source": {
    "source_id": "{{SOURCE_ID}}",
    "name": "{{SOURCE_NAME}}",
    "source_type": "pdf",
    "source_file": "{{PDF_FILENAME}}",
    "source_year": {{SOURCE_YEAR_OR_NULL}},
    "rights_status": "unknown"
  },
  "metadata": {
    "subject": "{{BOARD_SUBJECT}}",
    "board": "{{BOARD}}",
    "class_level": {{CLASS}},
    "academic_year": "{{ACADEMIC_YEAR}}"
  },
  "extraction_provider": "{{CLAUDE_OR_GEMINI}}",
  "extraction_model": "{{MODEL_IF_KNOWN}}",
  "questions": [
    {
      "question_id": "{{SOURCE_QUESTION_ID}}",
      "question_text": "...",
      "question_type": "mcq|vsaq|saq|laq",
      "answer_mode": "option_selection|manual_written_answer|final_answer_selection_and_handwritten_upload",
      "handwritten_upload_mode": "none",
      "subject": "{{BOARD_SUBJECT}}",
      "board": "{{BOARD}}",
      "class_level": {{CLASS}},
      "chapter": "{{EXACT_CANONICAL_CHAPTER_OR_NULL}}",
      "topic": "...",
      "subtopic": null,
      "difficulty": null,
      "competency": null,
      "marks": 1,
      "answer_choices": [],
      "correct_answer": null,
      "question_parts": [],
      "solution": null,
      "marking_scheme": null,
      "source_page": 1,
      "source_pages": [1],
      "source_question_number": "{{SOURCE_QUESTION_NUMBER}}",
      "assets": [],
      "diagram_reference": null,
      "extraction_confidence": 0.0,
      "extraction_warnings": [],
      "verification_status": "PENDING"
    }
  ]
}

FIELD RULES
- MCQ: answer_choices must preserve the source options. correct_answer should preferably be an option label such as A/B/C/D when it is explicitly known.
- VSAQ/SAQ/LAQ: answer_choices is normally [].
- Assertion-Reason questions may be represented as MCQ because they are option-selection questions; preserve the assertion/reason wording in question_text and preserve all options.
- Internal-choice OR questions: preserve the full structure in question_parts. Do not silently discard either alternative.
- Visual/diagram questions: include assets or diagram_reference when the source provides them; otherwise add an extraction warning.
- If a field is uncertain, use null and add a concise extraction warning.

FINAL SELF-CHECK BEFORE RETURNING JSON
- Is the JSON syntactically valid?
- Does every question have question_text, marks, question_type, subject, board and class_level?
- Are all question IDs unique within this batch?
- Are page numbers present where visible?
- Are all chapter values exact taxonomy names or null?
- Did you avoid inventing answers, chapters, diagrams or marks?
- Is verification_status PENDING for every question?
```

## 3. Claude-specific operating pattern

Claude's current consumer upload support includes PDF and JSON. Claude documents a 500 MB per-file chat upload limit and up to 20 files per chat; PDF visual analysis is supported for PDFs up to 100 pages, while larger PDFs are processed text-only. Free usage is session-limited and affected by message length, attachments and other usage factors. citeturn0search0turn0search11

For the lowest-cost workflow, use one source PDF per extraction request when possible. If the PDF is large, split it into logical page ranges and make each output carry the same source metadata plus accurate source pages.

Recommended Claude sequence:
1. Upload the PDF.
2. Upload/provide the canonical taxonomy JSON when needed.
3. Paste the Master extraction prompt.
4. Ask for JSON only.
5. Save the returned JSON without manually editing question content.
6. Upload the JSON to Improvia.

## 4. Gemini-specific operating pattern

Gemini Apps currently allow up to 10 files in one prompt, subject to availability, with non-video files up to 100 MB. The no-AI-plan context window is currently 32K tokens, and usage limits can change. citeturn0search15turn0search3

For extraction quality, do not use the ability to upload many PDFs as a reason to combine unrelated papers into one extraction job. Keep one paper/source per JSON batch so provenance and review remain clean.

## 5. Optional second-pass audit prompt

After Claude/Gemini generates the JSON, use this prompt in the same conversation before saving the file:

```text
Audit the JSON you just produced against the attached PDF.

Do NOT rewrite the questions yet.
Return a compact JSON audit object with:
- total_questions
- duplicate_source_ids
- missing_question_text
- missing_marks
- invalid_question_types
- missing_page_references
- noncanonical_chapter_values
- questions_with_diagrams_or_graphs
- questions_with_uncertain_answers
- questions_with_extraction_warnings
- other_issues

For every issue, identify the question_id and explain exactly what is uncertain.
Do not solve mathematics unless needed only to identify that an extracted answer is internally inconsistent.
Do not change VERIFIED/PENDING status. Treat all extracted questions as PENDING.
Return JSON only.
```

Use this audit to decide which questions need attention. The Improvia importer remains the actual gatekeeper.

## 6. Optional repair prompt

When the importer reports a structural or taxonomy problem, do not ask the model to regenerate the whole PDF extraction. Give it the original JSON and only the validation errors:

```text
Repair ONLY the listed JSON validation issues.

Do not change question wording, marks, source pages, answers, or other fields unless the listed issue requires that exact change.
Do not invent missing information.
For an uncertain chapter, set chapter to null rather than guessing.
Return the complete corrected JSON object and nothing else.

VALIDATION ERRORS:
{{PASTE_VALIDATION_ERRORS}}
```

## 7. Improvia upload workflow

From the teacher dashboard use **Import AI JSON**.

The upload screen accepts one or more `.json` files. Each file may itself contain many questions. Every file is independently parsed and sent through the shared ingestion pipeline.

For each uploaded batch:

1. JSON is parsed.
2. Top-level metadata/defaults are normalized.
3. Provider field aliases are normalized.
4. Question-type aliases are normalized.
5. Safe chapter/topic mappings are normalized.
6. Canonical curriculum resolution runs against `canonical_math_taxonomy_2026_27.json`.
7. Structural validation runs.
8. Duplicate fingerprints are checked.
9. The original JSON is persisted in the extraction review inbox.
10. Review items are persisted in the database.
11. Nothing is inserted into the live canonical question bank yet.

Exact repeat uploads receive a deterministic batch ID. Re-uploading the identical JSON therefore updates the same persisted batch instead of creating an unrelated batch identity.

## 8. Review workflow

Use the review dashboard to work through the queue gradually.

Recommended review order:
1. Invalid/validation-pending items.
2. Unresolved or ambiguous curriculum mappings.
3. Diagram/graph/image-dependent questions.
4. MCQ answer verification.
5. Remaining clean questions.

At review time verify:
- question wording
- question type
- marks
- board/class/subject
- exact canonical chapter
- topic/subtopic
- answer choices
- correct answer
- solution/marking scheme when supplied
- source page and question number
- diagram/assets
- licensing/rights status
- any extraction warning

Approval is the only point where a question becomes eligible for publication.

## 9. Canonical publication

Approved records go through the publication service and are written to the canonical question bank. The secondary database sync, when configured, is a downstream synchronization step; you do not manually enter each question into Aiven.

Therefore the operating unit is the JSON batch, not the individual database row.

## 10. Folder and naming convention

Keep generated files outside the application source tree, for example:

```text
question_sources/
  ICSE/
    Class10/
      Mathematics/
        2026-27/
          PDFs/
          JSON/
            ICSE_Class10_Maths_2026-27_Sample_01.json
            ICSE_Class10_Maths_2026-27_Sample_02.json
          Reviewed/
```

Do not manually edit a JSON file after it has been uploaded unless the change is intentional. Prefer a new JSON version so the review history remains understandable.

## 11. Scaling rule

Do not start with hundreds of questions in one untested batch.

Use this progression:

- Batch 1: the existing 51-question regression set.
- Batch 2: intentionally varied structures.
- Next: 20-50 questions per real PDF/source.
- Then: 100+ question batches after the review workflow has been used successfully.
- Only after repeated clean imports should you consider automated AI-assisted verification.

The database remains the canonical source of truth. JSON is the ingestion interface; it is not the permanent question-bank database.