"""PDF question extraction adapter for the source-agnostic ingestion layer.

This adapter intentionally stops at RawQuestion objects. It does not classify
chapters, verify answers, or publish questions. PDF extraction is inherently
format-sensitive, so uncertain/question-boundary cases remain reviewable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import fitz

from ..models import RawQuestion, SourceDocument, SourceType


QUESTION_START_RE = re.compile(
    r"^\s*(?:question\s*)?(?:q\.?\s*)?(\d{1,3})\s*[\.)\-:]?(?:\s+(.*))?$",
    re.IGNORECASE,
)
MCQ_OPTION_RE = re.compile(r"^\s*\(?([A-Da-d])\)?(?:[\.)]\s+|\s+)(.*)$")
MARKS_RE = re.compile(
    r"(?:\[|\()\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*(?:\]|\))\s*$",
    re.IGNORECASE,
)


class PDFAdapter:
    """Extract question candidates from PDFs with a usable text layer.

    Scanned/image-only pages are detected and flagged for a future OCR adapter.
    Embedded raster images are represented as asset metadata; binary extraction
    is deliberately kept out of the ingestion layer until storage is defined.
    """

    source_type = SourceType.PDF.value

    def __init__(self, source: SourceDocument):
        if source.source_type != self.source_type:
            raise ValueError("PDFAdapter requires a SourceDocument with source_type='pdf'.")
        if not source.file_path:
            raise ValueError("PDF SourceDocument.file_path is required.")
        self.source = source

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    @staticmethod
    def _question_start(line: str) -> Optional[Tuple[str, str]]:
        match = QUESTION_START_RE.match(line)
        if not match:
            return None
        # Reject bare section-like numbers unless they are followed by a
        # conventional delimiter. A bare number is accepted only as a question
        # boundary when the regex captured no suffix and can be followed by text
        # on the next line.
        number, text = match.group(1), (match.group(2) or "").strip()
        if not text and not re.search(r"\d\s*[\.)\-:]\s*$", line):
            return None
        return number, text

    @staticmethod
    def _extract_options(lines: Sequence[str]) -> Tuple[List[str], List[str]]:
        options: List[str] = []
        remaining: List[str] = []
        current_option: Optional[int] = None

        for line in lines:
            match = MCQ_OPTION_RE.match(line)
            if match:
                current_option = ord(match.group(1).upper()) - ord("A")
                while len(options) <= current_option:
                    options.append("")
                options[current_option] = match.group(2).strip()
            elif current_option is not None and line:
                options[current_option] = f"{options[current_option]} {line}".strip()
            else:
                remaining.append(line)

        if len(options) < 2:
            return [], list(lines)
        return options, remaining

    @staticmethod
    def _extract_marks(text: str) -> Optional[float]:
        matches = MARKS_RE.findall(text.strip())
        return float(matches[-1]) if matches else None

    @staticmethod
    def _page_assets(page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        assets: List[Dict[str, Any]] = []
        for image in page.get_images(full=True):
            xref = image[0]
            width = image[2]
            height = image[3]
            assets.append(
                {
                    "asset_type": "image",
                    "page_number": page_number,
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "source": "pdf_embedded_image",
                }
            )
        return assets

    def _parse_questions(
        self,
        pages: Sequence[Tuple[int, str, List[Dict[str, Any]]]],
    ) -> List[RawQuestion]:
        questions: List[RawQuestion] = []
        current: Optional[Dict[str, Any]] = None
        sequence = 0

        def flush() -> None:
            nonlocal current
            if not current:
                return
            body_lines = list(current["lines"])
            options, remaining = self._extract_options(body_lines)
            full_text = "\n".join(remaining).strip()
            marks = self._extract_marks(full_text)
            if marks is None:
                marks = current.get("marks")

            page_start = current["page_start"]
            page_end = current["page_end"]
            question_number = current["number"]
            raw_id = f"{self.source.source_id}-Q{sequence:04d}"
            source_reference = (
                f"pages {page_start}-{page_end}" if page_end != page_start else f"page {page_start}"
            )

            confidence = 0.65
            if len(full_text) >= 12:
                confidence += 0.15
            if options:
                confidence += 0.10
            if marks is not None:
                confidence += 0.05
            if page_end != page_start:
                confidence -= 0.05

            questions.append(
                RawQuestion(
                    raw_question_id=raw_id,
                    source_id=self.source.source_id,
                    raw_text=full_text,
                    raw_options=options,
                    raw_marks=marks,
                    source_reference=source_reference,
                    extraction_confidence=max(0.0, min(1.0, confidence)),
                    metadata={
                        "question_number": question_number,
                        "question_type": "mcq" if options else "saq",
                        "page_start": page_start,
                        "page_end": page_end,
                        "extraction_method": "pymupdf_text",
                        "needs_human_review": True,
                    },
                    raw_assets=list(current["assets"]),
                )
            )
            current = None

        for page_number, page_text, page_assets in pages:
            lines = self._clean_text(page_text).splitlines()
            for line in lines:
                start = self._question_start(line)
                if start:
                    flush()
                    sequence += 1
                    number, first_line = start
                    current = {
                        "number": number,
                        "lines": [first_line] if first_line else [],
                        "page_start": page_number,
                        "page_end": page_number,
                        "marks": None,
                        "assets": list(page_assets),
                    }
                elif current is not None:
                    current["lines"].append(line)
                    current["page_end"] = page_number
                    current["assets"].extend(page_assets)
        flush()
        return questions

    def ingest(self) -> List[RawQuestion]:
        """Extract numbered question candidates from the configured PDF."""
        path = Path(self.source.file_path or "")
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("PDFAdapter requires a .pdf file.")

        document = fitz.open(path)
        try:
            pages: List[Tuple[int, str, List[Dict[str, Any]]]] = []
            total_text_chars = 0
            ocr_pages: List[int] = []
            for index, page in enumerate(document, 1):
                text = page.get_text("text") or ""
                cleaned = text.strip()
                total_text_chars += len(cleaned)
                if not cleaned:
                    ocr_pages.append(index)
                pages.append((index, text, self._page_assets(page, index)))

            self.source.metadata.update(
                {
                    "page_count": len(document),
                    "text_char_count": total_text_chars,
                    "extraction_method": "pymupdf_text",
                    "ocr_required": bool(ocr_pages),
                    "ocr_pages": ocr_pages,
                }
            )
            if total_text_chars == 0:
                return []
            return self._parse_questions(pages)
        finally:
            document.close()


def extract_pdf_questions(
    file_path: str,
    *,
    source_id: str = "pdf",
    name: Optional[str] = None,
    source_year: Optional[int] = None,
    rights_status: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[SourceDocument, List[RawQuestion]]:
    """Convenience API returning the source record and extracted candidates."""
    source = SourceDocument(
        source_id=source_id,
        source_type=SourceType.PDF.value,
        name=name or Path(file_path).name,
        file_path=file_path,
        source_year=source_year,
        rights_status=rights_status,
        metadata=dict(metadata or {}),
    )
    return source, PDFAdapter(source).ingest()
