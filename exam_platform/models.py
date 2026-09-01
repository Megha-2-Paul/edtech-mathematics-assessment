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
    city: Optional[str] = None
    role: str = "student"
    class_level: Optional[int] = None
    board: Optional[str] = None
    school: Optional[str] = None
    registration_date: Optional[str] = None
    registration_source: Optional[str] = None
    status: str = "active"
    def to_dict(self): return asdict(self)

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
    board: Optional[str] = None
    test_date: Optional[str] = None
    test_type: str = "weekly"
    def to_dict(self): return asdict(self)

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
    subject: str = "Mathematics"
    board: Optional[str] = None
    class_level: Optional[int] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None
    difficulty: Optional[str] = None
    competency: Optional[str] = None
    source: Optional[str] = None
    source_year: Optional[int] = None
    status: str = "active"
    def __post_init__(self):
        if self.question_type == "subjective": self.question_type = "saq"
        if self.question_type not in {"mcq", "vsaq", "saq", "laq"}: self.question_type = "mcq"
        if self.handwritten_upload_mode not in {m.value for m in HandwrittenUploadMode}: self.handwritten_upload_mode = HandwrittenUploadMode.NONE.value
        if self.status not in {"active", "inactive"}: self.status = "active"
    @property
    def requires_handwritten_upload(self): return self.handwritten_upload_mode == HandwrittenUploadMode.REQUIRED.value
    def to_dict(self):
        return {"question_id":self.question_id,"question_type":self.question_type,"answer_mode":self.answer_mode,"question_content":[asdict(c) for c in self.question_content],"answer_choices":self.answer_choices,"correct_answer":self.correct_answer,"marks":self.marks,"handwritten_upload_mode":self.handwritten_upload_mode,"requires_handwritten_upload":self.requires_handwritten_upload,"subject":self.subject,"board":self.board,"class_level":self.class_level,"chapter":self.chapter,"topic":self.topic,"subtopic":self.subtopic,"difficulty":self.difficulty,"competency":self.competency,"source":self.source,"source_year":self.source_year,"status":self.status}

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
    score: Optional[float] = None
    percentage: Optional[float] = None
    attempt_rate: Optional[float] = None
    accuracy: Optional[float] = None
    time_taken_seconds: Optional[int] = None
    def to_dict(self): return {"attempt_id":self.attempt_id,"student_id":self.student_id,"test_id":self.test_id,"started_at":self.started_at.isoformat(),"submitted_at":self.submitted_at.isoformat() if self.submitted_at else None,"status":self.status,"score":self.score,"percentage":self.percentage,"attempt_rate":self.attempt_rate,"accuracy":self.accuracy,"time_taken_seconds":self.time_taken_seconds}

@dataclass
class Response:
    response_id: str
    attempt_id: str
    question_id: str
    selected_answer: Optional[str]
    answer_status: str = AnswerStatus.UNANSWERED.value
    marks_awarded: Optional[float] = None
    is_correct: Optional[bool] = None
    answered_at: Optional[datetime] = None
    def to_dict(self):
        data=asdict(self)
        if self.answered_at: data["answered_at"]=self.answered_at.isoformat()
        return data

@dataclass
class AnswerImage:
    image_id: str
    attempt_id: str
    question_id: str
    page_number: int
    original_filename: str
    file_path: str
    uploaded_at: datetime
    def to_dict(self): return {"image_id":self.image_id,"attempt_id":self.attempt_id,"question_id":self.question_id,"page_number":self.page_number,"original_filename":self.original_filename,"file_path":self.file_path,"uploaded_at":self.uploaded_at.isoformat()}
