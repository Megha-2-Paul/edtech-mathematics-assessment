"""Single-page Shaalaa question extraction.

This adapter intentionally handles only the rendered question-bank pattern used by
Shaalaa pages. It fetches one URL, identifies each question by the chapter/topic
marker that follows it, and emits the existing RawQuestion contract.

It does not crawl pagination, verify answers, download arbitrary assets, publish
questions, or persist anything to the database.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from ..models import RawQuestion, SourceDocument, SourceType
from .url import URLAdapter


SHAALAA_TOPIC_MARKER_RE = re.compile(r"^\s*\[(\d+)\]\s+(.+?)\s*$")
SHAALAA_CHAPTER_RE = re.compile(r"^\s*Chapter:\s*\[\d+\]\s+(.+?)\s*$", re.IGNORECASE)
SHAALAA_CONCEPT_RE = re.compile(r"^\s*Concept:\s*", re.IGNORECASE)


class ShaalaaPageParser:
    """Extract individual questions from one Shaalaa question-bank page."""

    source_type = SourceType.URL.value

    def __init__(
        self,
        source: SourceDocument,
        *,
        timeout: int = 20,
        max_bytes: int = 5_000_000,
    ) -> None:
        if source.source_type != self.source_type:
            raise ValueError("ShaalaaPageParser requires source_type='url'.")
        if not source.url:
            raise ValueError("Shaalaa source URL is required.")
        parsed = urlparse(source.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Shaalaa source URL must be a valid http(s) URL.")
        if "shaalaa.com" not in parsed.netloc.lower():
            raise ValueError("ShaalaaPageParser only accepts shaalaa.com URLs.")
        self.source = source
        self.timeout = timeout
        self.max_bytes = max_bytes

    @staticmethod
    def _clean_question_blocks(blocks: List[str]) -> Tuple[str, Optional[str], bool]:
        """Combine question blocks and extract source metadata without treating the
        Shaalaa topic index as question marks.
        """
        question_parts: List[str] = []
        topic: Optional[str] = None
        contains_image = False

        for block in blocks:
            text = re.sub(r"\s+", " ", block).strip()
            if not text:
                continue
            if text.upper() == "VIEW SOLUTION":
                continue
            if SHAALAA_CHAPTER_RE.match(text):
                chapter_match = SHAALAA_CHAPTER_RE.match(text)
                if chapter_match:
                    topic = chapter_match.group(1).strip()
                continue
            if SHAALAA_CONCEPT_RE.match(text):
                continue
            if text == "Image":
                contains_image = True
                continue
            question_parts.append(text)

        return " ".join(question_parts).strip(), topic, contains_image

    @classmethod
    def _parse_blocks(cls, blocks: List[str], source_id: str) -> List[RawQuestion]:
        """Parse the rendered Shaalaa block sequence.

        On the target page each question is followed by a marker such as
        ``[2] Banking``. The number is a Shaalaa topic/chapter index, NOT the
        question's marks. Therefore marks remain unset unless a future source
        pattern provides an unambiguous marks field.
        """
        questions: List[RawQuestion] = []
        pending: List[str] = []
        sequence = 0
        current_topic: Optional[str] = None

        for index, block in enumerate(blocks):
            marker = SHAALAA_TOPIC_MARKER_RE.match(block)
            if marker:
                text, chapter_from_block, contains_image = cls._clean_question_blocks(pending)
                topic = chapter_from_block or current_topic or marker.group(2).strip()
                if len(text) >= 8:
                    sequence += 1
                    questions.append(
                        RawQuestion(
                            raw_question_id=f"{source_id}-Q{sequence:04d}",
                            source_id=source_id,
                            raw_text=text,
                            raw_options=[],
                            raw_answer=None,
                            raw_marks=None,
                            raw_assets=[],
                            source_reference=f"url:block:{index} | topic:{topic}",
                            extraction_confidence=0.90 if not contains_image else 0.78,
                            metadata={
                                "question_number": sequence,
                                "question_type": "saq",
                                "chapter_hint": topic,
                                "topic_hint": topic,
                                "shaalaa_topic_index": int(marker.group(1)),
                                "contains_image": contains_image,
                                "extraction_method": "shaalaa_single_page_parser",
                                "needs_human_review": True,
                                "marks_source": "not_explicitly_available",
                            },
                        )
                    )
                pending = []
                current_topic = marker.group(2).strip()
                continue

            # Navigation/footer text after the question list should not become a
            # candidate. We only accumulate content until a topic marker appears.
            if len(block.strip()) > 0:
                pending.append(block)

        return questions

    def ingest(self) -> List[RawQuestion]:
        """Fetch exactly one Shaalaa page and return review-only candidates."""
        source_html = URLAdapter(
            self.source,
            timeout=self.timeout,
            max_bytes=self.max_bytes,
        ).fetch_html()
        blocks = URLAdapter._visible_blocks(source_html)
        questions = self._parse_blocks(blocks, self.source.source_id)

        self.source.metadata.update(
            {
                "extraction_method": "shaalaa_single_page_parser",
                "content_type": "text/html",
                "block_count": len(blocks),
                "extracted_question_count": len(questions),
                "needs_human_review": True,
                "pagination_crawled": False,
            }
        )
        return questions


def extract_shaalaa_page(
    url: str,
    *,
    source_id: str = "shaalaa",
    name: Optional[str] = None,
    source_year: Optional[int] = None,
    rights_status: str = "unknown",
    metadata: Optional[Dict[str, object]] = None,
) -> Tuple[SourceDocument, List[RawQuestion]]:
    """Convenience API for one Shaalaa page only."""
    source = SourceDocument(
        source_id=source_id,
        source_type=SourceType.URL.value,
        name=name or "Shaalaa question-bank page",
        url=url,
        source_year=source_year,
        rights_status=rights_status,
        metadata=dict(metadata or {}),
    )
    return source, ShaalaaPageParser(source).ingest()
