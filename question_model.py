from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, List, Optional, Union


BOARD_CHOICES = {"CBSE", "ICSE"}
QUESTION_TYPE_CHOICES = {
    "mcq",
    "short_answer",
    "long_answer",
    "case_study",
    "numerical",
    "match_the_following",
    "true_false",
    "mixed",
}
DIFFICULTY_CHOICES = {"easy", "moderate", "hard", "very_hard"}
COMPETENCY_CHOICES = {
    "conceptual_understanding",
    "procedural_knowledge",
    "application",
    "reasoning",
    "higher_order",
}
EXTRACTION_STATUS_CHOICES = {"raw", "extracted", "normalized", "needs_review", "rejected"}
VALIDATION_STATUS_CHOICES = {"pending", "valid", "warning", "invalid"}
STATUS_CHOICES = {"active", "archived"}

VALID_CLASS_LEVELS = {10, 11, 12}


@dataclass
class ValidationIssue:
    level: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "field": self.field,
            "message": self.message,
        }


@dataclass
class QuestionValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, field: str, message: str) -> None:
        self.errors.append(message)
        self.issues.append(ValidationIssue(level="error", field=field, message=message))

    def add_warning(self, field: str, message: str) -> None:
        self.warnings.append(message)
        self.issues.append(ValidationIssue(level="warning", field=field, message=message))

    def finalize(self) -> None:
        self.valid = len(self.errors) == 0


@dataclass
class Question:
    question_id: str
    board: str
    class_level: int
    subject: str
    chapter: str
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    question_type: str = ""
    difficulty: Optional[str] = None
    competency: Optional[str] = None
    marks: int = 0
    question_text: str = ""
    instructions: Optional[str] = None
    options: Optional[List[dict[str, Any]]] = None
    correct_answer: Optional[str] = None
    solution: Optional[str] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_year: Optional[int] = None
    source_exam: Optional[str] = None
    source_page: Optional[int] = None
    source_question_number: Optional[str] = None
    image_assets: Optional[List[dict[str, Any]]] = None
    subquestions: Optional[List[dict[str, Any]]] = None
    internal_choices: Optional[List[dict[str, Any]]] = None
    extraction_status: str = "raw"
    validation_status: str = "pending"
    validation_notes: Optional[List[str]] = None
    status: str = "active"
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Question":
        return cls(**data)

    def validate(self, seen_ids: Optional[set[str]] = None) -> QuestionValidationResult:
        return validate_question(self, seen_ids=seen_ids)


def validate_question(question: Union[Question, dict[str, Any]], seen_ids: Optional[set[str]] = None) -> QuestionValidationResult:
    if isinstance(question, dict):
        question = Question.from_dict(question)

    result = QuestionValidationResult(valid=True, errors=[], warnings=[], issues=[])

    question_id = (question.question_id or "").strip()
    if not question_id:
        result.add_error("question_id", "question_id is required.")
    elif not question_id.startswith("Q_"):
        result.add_error("question_id", "question_id must use the format Q_000001.")
    else:
        if seen_ids is not None and question_id in seen_ids:
            result.add_error("question_id", f"question_id '{question_id}' is not unique.")

    if question.board not in BOARD_CHOICES:
        result.add_error("board", f"board must be one of: {sorted(BOARD_CHOICES)}.")

    if not isinstance(question.class_level, int) or isinstance(question.class_level, bool):
        result.add_error("class_level", "class_level must be an integer.")
    elif question.class_level not in VALID_CLASS_LEVELS:
        result.add_error("class_level", "class_level must be a valid value in the range 10-12.")

    if not question.subject or not question.subject.strip():
        result.add_error("subject", "subject is required.")

    if not question.chapter or not question.chapter.strip():
        result.add_error("chapter", "chapter is required.")

    if question.question_type not in QUESTION_TYPE_CHOICES:
        result.add_error("question_type", f"question_type must be one of: {sorted(QUESTION_TYPE_CHOICES)}.")

    if not isinstance(question.marks, int) or isinstance(question.marks, bool):
        result.add_error("marks", "marks must be a positive integer.")
    elif question.marks <= 0:
        result.add_error("marks", "marks must be a positive integer.")

    if not question.question_text or not question.question_text.strip():
        result.add_error("question_text", "question_text is required.")

    if question.difficulty is not None and question.difficulty not in DIFFICULTY_CHOICES:
        result.add_error("difficulty", f"difficulty must be one of: {sorted(DIFFICULTY_CHOICES)}.")

    if question.competency is not None and question.competency not in COMPETENCY_CHOICES:
        result.add_error("competency", f"competency must be one of: {sorted(COMPETENCY_CHOICES)}.")

    if question.extraction_status not in EXTRACTION_STATUS_CHOICES:
        result.add_error("extraction_status", f"extraction_status must be one of: {sorted(EXTRACTION_STATUS_CHOICES)}.")

    if question.validation_status not in VALIDATION_STATUS_CHOICES:
        result.add_error("validation_status", f"validation_status must be one of: {sorted(VALIDATION_STATUS_CHOICES)}.")

    if question.status not in STATUS_CHOICES:
        result.add_error("status", f"status must be one of: {sorted(STATUS_CHOICES)}.")

    if question.question_type == "mcq":
        options = question.options or []
        if not options:
            result.add_error("options", "MCQ questions must include options.")
        else:
            option_ids = []
            for idx, option in enumerate(options):
                if not isinstance(option, dict):
                    result.add_error("options", f"Option at index {idx} must be a dictionary.")
                    continue
                option_id = option.get("id")
                option_text = option.get("text")
                if option_id is None or str(option_id).strip() == "":
                    result.add_error("options", f"Option at index {idx} is missing an id.")
                if option_text is None or str(option_text).strip() == "":
                    result.add_error("options", f"Option '{option_id}' is empty.")
                if option_id is not None:
                    option_ids.append(str(option_id))

            if len(option_ids) != len(set(option_ids)):
                result.add_error("options", "MCQ option IDs must be unique.")

        if question.validation_status in {"valid", "warning", "invalid"} and not question.correct_answer:
            result.add_error("correct_answer", "MCQ questions require a correct_answer when validation is complete.")
        elif question.question_type == "mcq" and question.correct_answer is not None:
            valid_option_ids = {str(option.get("id")) for option in (question.options or []) if isinstance(option, dict)}
            if valid_option_ids and str(question.correct_answer) not in valid_option_ids:
                result.add_error("correct_answer", "correct_answer must match a valid option id.")
        elif question.question_type == "mcq" and not question.correct_answer and question.validation_status == "pending":
            result.add_warning("correct_answer", "MCQ questions should include a correct_answer during validation.")

    if question.validation_status == "pending":
        result.add_warning("validation_status", "This question has not yet completed validation.")

    result.finalize()
    return result


def validate_question_list(questions: Iterable[Union[Question, dict[str, Any]]]) -> list[QuestionValidationResult]:
    seen_ids: set[str] = set()
    results: list[QuestionValidationResult] = []
    for q in questions:
        result = validate_question(q, seen_ids=seen_ids)
        results.append(result)
        if isinstance(q, dict):
            question_id = str((q.get("question_id") or "")).strip()
        else:
            question_id = str((q.question_id or "")).strip()
        if question_id.startswith("Q_"):
            seen_ids.add(question_id)
    return results
