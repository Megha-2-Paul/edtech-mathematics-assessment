"""Input adapters for question ingestion."""

from .manual import ManualAdapter
from .pdf import PDFAdapter, extract_pdf_questions
from .url import URLAdapter, extract_url_questions
from .shaalaa import ShaalaaPageParser, extract_shaalaa_page

__all__ = [
    "ManualAdapter",
    "PDFAdapter",
    "URLAdapter",
    "ShaalaaPageParser",
    "extract_pdf_questions",
    "extract_url_questions",
    "extract_shaalaa_page",
]
