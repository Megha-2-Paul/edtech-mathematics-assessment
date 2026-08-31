from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContentBlock:
    type: str
    value: Any = None
    asset_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestionRecord:
    question_number: str
    section: Optional[str]
    marks: Optional[int]
    content: List[ContentBlock] = field(default_factory=list)
    subquestions: List["QuestionRecord"] = field(default_factory=list)
    source_container: Optional[str] = None


@dataclass
class PaperRecord:
    paper: Dict[str, Any]
    questions: List[QuestionRecord]
    assets: List[Dict[str, Any]] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
