from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Any, Dict
from enum import Enum


class AttemptStatus(Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class AnswerStatus(Enum):
    ANSWERED = "answered"
    UNANSWERED = "unanswered"
    PARTIAL = "partial"


class HandwrittenUploadMode(Enum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


@dataclass
class ContentBlock:
    type: str
    value: Any = None
    asset_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Student:
    student_id: str
    name: str
    email: str
    phone: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Test:
    test_id: str
    title: str
    subject: str
    class_level: int
    duration_minutes: int
    total_marks: int
    questions: List[str] = field(default_factory=list)
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Question:
    question_id: str
    question_type: str
    answer_mode: str
    question_content: List[ContentBlock]
    answer_choices: List[str]
    correct_answer: Optional[str]
    marks: int
    handwritten_upload_mode: str = HandwrittenUploadMode.NONE.value

    def __post_init__(self):
        # Backward-compatible normalization for existing/demo data.
        if self.handwritten_upload_mode not in {m.value for m in HandwrittenUploadMode}:
            self.handwritten_upload_mode = HandwrittenUploadMode.NONE.value

    @property
    def requires_handwritten_upload(self) -> bool:
        return self.handwritten_upload_mode == HandwrittenUploadMode.REQUIRED.value

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "question_type": self.question_type,
            "answer_mode": self.answer_mode,
            "question_content": [asdict(c) for c in self.question_content],
            "answer_choices": self.answer_choices,
            "correct_answer": self.correct_answer,
            "marks": self.marks,
            "handwritten_upload_mode": self.handwritten_upload_mode,
            "requires_handwritten_upload": self.requires_handwritten_upload,
        }


@dataclass
class TestQuestion:
    test_id: str
    question_id: str
    sequence_number: int
    marks: int


@dataclass
class Attempt:
    attempt_id: str
    student_id: str
    test_id: str
    started_at: datetime
    submitted_at: Optional[datetime] = None
    status: str = AttemptStatus.IN_PROGRESS.value

    def to_dict(self) -> dict:
        return {
            "attempt_id": self.attempt_id,
            "student_id": self.student_id,
            "test_id": self.test_id,
            "started_at": self.started_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "status": self.status,
        }


@dataclass
class Response:
    response_id: str
    attempt_id: str
    question_id: str
    selected_answer: Optional[str]
    answer_status: str = AnswerStatus.UNANSWERED.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AnswerImage:
    image_id: str
    attempt_id: str
    question_id: str
    page_number: int
    original_filename: str
    file_path: str
    uploaded_at: datetime

    def to_dict(self) -> dict:
        return {
            "image_id": self.image_id,
            "attempt_id": self.attempt_id,
            "question_id": self.question_id,
            "page_number": self.page_number,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "uploaded_at": self.uploaded_at.isoformat(),
        }
