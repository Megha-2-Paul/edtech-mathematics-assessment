"""Manual adapter used as the first concrete ingestion source.

The adapter deliberately emits the same RawQuestion contract that future PDF,
URL, image/OCR, API and partner adapters will emit.
"""

from typing import Any, Dict, Iterable, List, Optional

from ..models import RawQuestion, SourceDocument, SourceType


class ManualAdapter:
    source_type = SourceType.MANUAL.value

    def __init__(self, source: Optional[SourceDocument] = None):
        self.source = source or SourceDocument(
            source_id="manual",
            source_type=self.source_type,
            name="Manual entry",
        )

    def ingest(self, records: Iterable[Dict[str, Any]]) -> List[RawQuestion]:
        """Convert manually supplied dictionaries into RawQuestion objects."""

        questions = []
        for index, record in enumerate(records, 1):
            raw_id = str(record.get("raw_question_id") or f"{self.source.source_id}-{index}")
            questions.append(
                RawQuestion(
                    raw_question_id=raw_id,
                    source_id=self.source.source_id,
                    raw_text=str(record.get("raw_text", "")).strip(),
                    raw_options=list(record.get("raw_options") or []),
                    raw_answer=record.get("raw_answer"),
                    raw_marks=record.get("raw_marks"),
                    raw_assets=list(record.get("raw_assets") or []),
                    source_reference=record.get("source_reference"),
                    extraction_confidence=1.0,
                    metadata=dict(record.get("metadata") or {}),
                )
            )
        return questions
