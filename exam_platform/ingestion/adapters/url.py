"""URL-based question extraction for the source-agnostic ingestion layer.

The adapter fetches HTML and produces RawQuestion candidates only. It deliberately
stops before publication, answer verification, curriculum mapping, or persistence.
A small amount of source-aware handling is provided for question-bank pages whose
HTML is mostly rendered text; the core contract remains source-agnostic.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..models import RawQuestion, SourceDocument, SourceType


QUESTION_START_RE = re.compile(
    r"^\s*(?:question\s*)?(?:q\.?\s*)?(\d{1,3})\s*[\.)\-:]\s*(.*)$",
    re.IGNORECASE,
)
OPTION_RE = re.compile(r"^\s*\(?([A-Da-d])\)?[\.)]\s*(.+)$")
MARKS_RE = re.compile(
    r"(?:\[|\(|\{|\b)\s*(\d+(?:\.\d+)?)\s*(?:marks?|m)\s*(?:\]|\)|\})?\s*$",
    re.IGNORECASE,
)


class _TextHTMLParser(HTMLParser):
    """Extract visible text blocks while ignoring scripts/styles/navigation noise."""

    SKIP_TAGS = {"script", "style", "noscript", "svg"}
    BLOCK_TAGS = {
        "p", "div", "li", "section", "article", "main", "h1", "h2", "h3",
        "h4", "h5", "h6", "br", "tr", "td", "th", "blockquote"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: List[str] = []
        self._parts: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if cleaned:
            self._parts.append(cleaned)

    def _flush(self) -> None:
        if self._parts:
            text = " ".join(self._parts).strip()
            if text:
                self.blocks.append(text)
        self._parts = []

    def close(self) -> None:
        super().close()
        self._flush()


class URLAdapter:
    """Fetch a public HTML page and extract numbered question candidates."""

    source_type = SourceType.URL.value

    def __init__(
        self,
        source: SourceDocument,
        *,
        timeout: int = 20,
        max_bytes: int = 5_000_000,
        user_agent: str = "ImproviaQuestionIngestion/1.0",
    ) -> None:
        if source.source_type != self.source_type:
            raise ValueError("URLAdapter requires source_type='url'.")
        if not source.url:
            raise ValueError("URL SourceDocument.url is required.")
        parsed = urlparse(source.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL must be a valid http(s) URL.")
        self.source = source
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.user_agent = user_agent

    def fetch_html(self) -> str:
        request = Request(
            self.source.url or "",
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
        )
        with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and "html" not in content_type:
                raise ValueError(f"URL did not return HTML content: {content_type}")
            payload = response.read(self.max_bytes + 1)
        if len(payload) > self.max_bytes:
            raise ValueError(f"HTML response exceeds {self.max_bytes} byte limit.")
        return payload.decode("utf-8", errors="replace")

    @staticmethod
    def _visible_blocks(source_html: str) -> List[str]:
        parser = _TextHTMLParser()
        parser.feed(source_html)
        parser.close()
        # Collapse accidental duplicate whitespace while preserving useful blocks.
        return [re.sub(r"\s+", " ", block).strip() for block in parser.blocks if block.strip()]

    @staticmethod
    def _parse_marks(text: str) -> Optional[float]:
        matches = MARKS_RE.findall(text)
        return float(matches[-1]) if matches else None

    @classmethod
    def _parse_questions(cls, blocks: List[str], source_id: str) -> List[RawQuestion]:
        questions: List[RawQuestion] = []
        current: Optional[Dict[str, object]] = None
        sequence = 0

        def flush() -> None:
            nonlocal current, sequence
            if not current:
                return
            lines = list(current["lines"])  # type: ignore[arg-type]
            options: List[str] = []
            remaining: List[str] = []
            option_indexes: Dict[str, int] = {}
            for line in lines:
                match = OPTION_RE.match(line)
                if match:
                    label = match.group(1).upper()
                    index = ord(label) - ord("A")
                    option_indexes[label] = index
                    while len(options) <= index:
                        options.append("")
                    options[index] = match.group(2).strip()
                else:
                    remaining.append(line)

            text = " ".join(remaining).strip()
            marks = cls._parse_marks(text)
            number = str(current["number"])
            if len(text) < 8:
                current = None
                return

            sequence += 1
            confidence = 0.55
            if len(text) >= 30:
                confidence += 0.15
            if len(options) >= 2:
                confidence += 0.10
            if marks is not None:
                confidence += 0.10
            if current.get("chapter"):
                confidence += 0.05

            questions.append(
                RawQuestion(
                    raw_question_id=f"{source_id}-Q{sequence:04d}",
                    source_id=source_id,
                    raw_text=text,
                    raw_options=options,
                    raw_marks=marks,
                    source_reference=f"url:{current.get('block_index', '?')} | question {number}",
                    extraction_confidence=min(1.0, confidence),
                    metadata={
                        "question_number": number,
                        "question_type": "mcq" if len(options) >= 2 else "saq",
                        "chapter_hint": current.get("chapter"),
                        "extraction_method": "html_text_parser",
                        "needs_human_review": True,
                    },
                )
            )
            current = None

        chapter_hint: Optional[str] = None
        for index, block in enumerate(blocks):
            start = QUESTION_START_RE.match(block)
            if start:
                flush()
                number, first_line = start.groups()
                current = {
                    "number": number,
                    "lines": [first_line],
                    "block_index": index,
                    "chapter": chapter_hint,
                }
                continue

            # Topic/chapter headings often occur immediately before question groups.
            if current is None and len(block) <= 100 and not block.endswith("?"):
                if any(word in block.lower() for word in (
                    "chapter", "compound interest", "gst", "banking", "shares",
                    "linear inequations", "quadratic equations", "matrices",
                    "coordinate geometry", "similarity", "circles", "statistics", "probability",
                )):
                    chapter_hint = block
            elif current is not None:
                current["lines"].append(block)  # type: ignore[union-attr]
        flush()
        return questions

    def ingest(self) -> List[RawQuestion]:
        """Fetch and extract question candidates without publishing them."""
        source_html = self.fetch_html()
        blocks = self._visible_blocks(source_html)
        questions = self._parse_questions(blocks, self.source.source_id)
        self.source.metadata.update(
            {
                "extraction_method": "html_text_parser",
                "content_type": "text/html",
                "block_count": len(blocks),
                "extracted_question_count": len(questions),
                "needs_human_review": True,
            }
        )
        return questions


def extract_url_questions(
    url: str,
    *,
    source_id: str = "url",
    name: Optional[str] = None,
    source_year: Optional[int] = None,
    rights_status: str = "unknown",
    metadata: Optional[Dict[str, object]] = None,
) -> Tuple[SourceDocument, List[RawQuestion]]:
    """Convenience API returning the source record and extracted candidates."""
    source = SourceDocument(
        source_id=source_id,
        source_type=SourceType.URL.value,
        name=name or urlparse(url).netloc,
        url=url,
        source_year=source_year,
        rights_status=rights_status,
        metadata=dict(metadata or {}),
    )
    return source, URLAdapter(source).ingest()
