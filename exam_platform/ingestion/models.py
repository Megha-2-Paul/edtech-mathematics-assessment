"""Internal data contracts for source-agnostic question ingestion."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    MANUAL = "manual"
    PDF = "pdf"
    URL = "url"
    IMAGE = "image"
    API = "api"
    AI_JSON = "ai_json"
    PARTNER = "partner"
    ORIGINAL = "original"


class IngestionStatus(str, Enum):
    EXTRACTED = "extracted"
    NORMALIZED = "normalized"
    VALIDATION_PENDING = "validation_pending"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"
    OUTDATED = "outdated"


@dataclass
class SourceDocument:
    """A source item from which one or more questions may be derived."""

    source_id: str
    source_type: str
    name: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    source_year: Optional[int] = None
    rights_status: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RawQuestion:
    """Extractor output before it is mapped to the canonical pre-publication model."""

    raw_question_id: str
    source_id: str
    raw_text: str
    raw_options: List[str] = field(default_factory=list)
    raw_answer: Optional[str] = None
    raw_marks: Optional[float] = None
    raw_assets: List[Dict[str, Any]] = field(default_factory=list)
    source_reference: Optional[str] = None
    extraction_confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedQuestion:
    """Canonical question representation used before publication to the bank."""

    raw_question_id: str
    question_type: str
    answer_mode: str
    question_text: str
    answer_choices: List[str] = field(default_factory=list)
    correct_answer: Optional[str] = None
    marks: float = 1
    handwritten_upload_mode: str = "none"
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
    source_type: str = SourceType.MANUAL.value
    assets: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Deterministic validation outcome; warnings do not necessarily block review."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: Optional[float] = None


@dataclass
class IngestionCandidate:
    """A normalized question plus its pipeline state."""

    question: NormalizedQuestion
    status: str = IngestionStatus.VALIDATION_PENDING.value
    validation: Optional[ValidationResult] = None
    duplicate_of: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)
