"""Canonical AI extraction contract aligned with the current question database.

This module is the single vocabulary/alias reference for external-AI JSON.
Providers may emit supported aliases, but the extractor must normalize them
into these canonical field names before ingestion.
"""

QUESTION_FIELDS = {
    "question_number": "source question number; never the canonical DB ID",
    "question_text": "questions.question_content_json text block",
    "question_parts": "structured subquestions/parts; preserve source structure",
    "answer_choices": "questions.answer_choices_json",
    "correct_answer": "questions.correct_answer when applicable/known",
    "marks": "questions.marks",
    "question_type": "questions.question_type: mcq|vsaq|saq|laq",
    "answer_mode": "questions.answer_mode",
    "handwritten_upload_mode": "questions.handwritten_upload_mode",
    "subject": "questions.subject",
    "board": "questions.board",
    "class_level": "questions.class_level",
    "chapter": "questions.chapter",
    "topic": "questions.topic",
    "subtopic": "questions.subtopic",
    "difficulty": "questions.difficulty",
    "competency": "questions.competency",
    "source": "questions.source",
    "source_year": "questions.source_year",
}

# Provider-facing aliases. The first entry is always the canonical key.
FIELD_ALIASES = {
    "question_text": ("question_text", "text", "question"),
    "question_type": ("question_type", "type"),
    "answer_choices": ("answer_choices", "options"),
    "class_level": ("class_level", "class"),
    "question_parts": ("question_parts", "parts", "subquestions"),
    "source_page": ("source_page", "page_number", "page"),
    "source_pages": ("source_pages", "pages"),
    "source_file": ("source_file", "source_pdf", "file_path", "file"),
    "extraction_provider": ("extraction_provider", "provider"),
    "extraction_model": ("extraction_model", "model"),
    "extraction_run_id": ("extraction_run_id", "run_id"),
}

PROVENANCE_FIELDS = {
    "source_pdf", "source_page", "source_pages", "source_question_number",
    "source_occurrence_id", "diagram_reference", "assets",
    "extraction_provider", "extraction_model", "extraction_run_id",
    "extraction_confidence", "extraction_warnings",
    "verification_status", "verification_note",
}

ALLOWED_QUESTION_TYPES = ("mcq", "vsaq", "saq", "laq")
ALLOWED_UPLOAD_MODES = ("none", "optional", "required")

# Fields that must never be invented when the PDF does not establish them.
INFERRED_FIELDS_REQUIRE_HUMAN_VERIFICATION = (
    "chapter", "topic", "subtopic", "difficulty", "competency", "correct_answer",
)

EXTRACTION_SCHEMA_VERSION = "1.0"
