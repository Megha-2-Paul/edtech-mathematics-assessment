# AI extraction contract

The provider layer should produce one JSON file per source PDF and place it in `extraction_inbox/`.

The human-review interface reads this contract and **does not import anything into the canonical question bank automatically**.

## Minimum JSON

```json
{
  "source_pdf": "CBSE_Class12_Mathematics_2026_MainRegular_Mathematics_12.pdf",
  "provider": "gemini",
  "model": "model-name",
  "prompt_version": "question_extraction_v1",
  "questions": [
    {
      "question_number": "1",
      "page_number": 3,
      "question_text": "Exact question text from the source PDF",
      "marks": 1,
      "question_type": "MCQ",
      "answer_choices": ["...", "...", "...", "..."],
      "correct_answer": null,
      "diagram_reference": null,
      "chapter": null,
      "topic": null,
      "competency": null,
      "difficulty": null
    }
  ]
}
```

## Rules

1. Preserve mathematical notation as faithfully as possible.
2. Do not invent missing text, marks, options, diagrams or answers.
3. Keep subquestions grouped under their parent question; the provider may add a `subquestions` array when needed.
4. Record the source page for every question. If a question continues onto another page, add `page_end` and keep the question as one record.
5. Diagrams/tables/graphs must be referenced rather than silently discarded.
6. Classification fields may be `null` during the extraction stage. Human verification is the gate before canonical import.
7. Raw provider output should be retained separately from the normalized record.

The provider worker can later support Gemini, Claude, PDF.co and other providers without changing the review UI, provided they emit this contract.
