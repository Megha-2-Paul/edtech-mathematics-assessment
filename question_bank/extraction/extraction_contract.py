"""Canonical AI extraction contract aligned with the current question database."""

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
