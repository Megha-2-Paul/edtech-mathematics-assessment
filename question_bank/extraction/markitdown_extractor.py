"""MarkItDown-based PDF document extraction.

This module is deliberately separate from question parsing. It converts a PDF
into a Markdown/text representation that downstream extractors can inspect.
Page geometry and source visuals remain the responsibility of the existing
PyMuPDF-based extraction layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown


@dataclass(frozen=True)
class MarkItDownResult:
    """Normalized result from a MarkItDown PDF conversion."""

    file_path: str
    markdown: str
    text: str
    extraction_method: str = "markitdown"
    provider_version: str = "0.1.7"

    @property
    def character_count(self) -> int:
        return len(self.text.strip())

    @property
    def is_empty(self) -> bool:
        return not bool(self.text.strip())


class MarkItDownPDFExtractor:
    """Convert a local PDF into Markdown/text using MarkItDown."""

    def __init__(self) -> None:
        self._converter = MarkItDown(enable_plugins=False)

    def extract(self, file_path: str | Path) -> MarkItDownResult:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("MarkItDownPDFExtractor requires a .pdf file.")

        result = self._converter.convert(str(path))
        markdown = getattr(result, "markdown", "") or ""
        text = getattr(result, "text_content", "") or markdown

        return MarkItDownResult(
            file_path=str(path),
            markdown=markdown,
            text=text,
        )


def extract_pdf_markdown(file_path: str | Path) -> MarkItDownResult:
    """Convenience wrapper for MarkItDown PDF conversion."""
    return MarkItDownPDFExtractor().extract(file_path)
