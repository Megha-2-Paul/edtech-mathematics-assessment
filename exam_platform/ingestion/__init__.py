"""Source-agnostic question ingestion and review pipeline.

The ingestion layer converts external content (manual entry today, PDF/URL/image/API
sources later) into the same normalized question representation used by the core
assessment platform.
"""

from .models import (
    IngestionStatus,
    NormalizedQuestion,
    RawQuestion,
    SourceDocument,
    SourceType,
    ValidationResult,
)
from .pipeline import QuestionIngestionPipeline

__all__ = [
    "IngestionStatus",
    "NormalizedQuestion",
    "RawQuestion",
    "SourceDocument",
    "SourceType",
    "ValidationResult",
    "QuestionIngestionPipeline",
]
