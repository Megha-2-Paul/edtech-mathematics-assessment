"""Input adapters for question ingestion."""

from .manual import ManualAdapter
from .pdf import PDFAdapter, extract_pdf_questions
from .url import URLAdapter, extract_url_questions

__all__ = [
    "ManualAdapter",
    "PDFAdapter",
    "URLAdapter",
    "extract_pdf_questions",
    "extract_url_questions",
]
