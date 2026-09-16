"""Helpers for preserving question-source provenance."""

from typing import Any, Dict, Optional

from .models import SourceDocument


def build_provenance(
    source: SourceDocument,
    *,
    source_reference: Optional[str] = None,
    extraction_method: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a serializable provenance record for an ingestion candidate."""

    return {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "source_name": source.name,
        "source_url": source.url,
        "source_file": source.file_path,
        "source_year": source.source_year,
        "rights_status": source.rights_status,
        "source_reference": source_reference,
        "extraction_method": extraction_method,
        "metadata": dict(source.metadata),
    }
