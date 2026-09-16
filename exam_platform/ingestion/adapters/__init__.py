"""Input adapters for question ingestion."""

from .manual import ManualAdapter
from .pdf import PDFAdapter, extract_pdf_questions

__all__ = ["ManualAdapter", "PDFAdapter", "extract_pdf_questions"]
