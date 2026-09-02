"""CBSE Board Paper agent.

Document-level routing is intentionally the primary language strategy. For
bilingual CBSE papers that follow an alternating Hindi/English layout, the
agent detects the pattern once and routes pages from that pattern instead of
independently classifying every page. Page-level signals remain safeguards.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from question_bank.agents.base import AgentResult, DocumentAgent, PageDecision

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
ENGLISH_WORD_RE = re.compile(r"\b(?:the|question|section|marks|find|solve|calculate|prove|show)\b", re.I)
QUESTION_RE = re.compile(r"\b(?:Q\.?\s*)?\d{1,2}\s*[.)]", re.I)


class CBSEBoardPaperAgent:
    """Route pages belonging to the CBSE board-paper document family."""

    name = "CBSE Board Paper"
    document_type = "CBSE_BOARD_PAPER"

    def _page_signal(self, page: Any) -> dict[str, Any]:
        text = page.get_text("text") or ""
        devanagari = len(DEVANAGARI_RE.findall(text))
        english_words = len(ENGLISH_WORD_RE.findall(text))
        question_markers = len(QUESTION_RE.findall(text))
        return {
            "text_length": len(text),
            "devanagari_count": devanagari,
            "english_word_count": english_words,
            "question_marker_count": question_markers,
        }

    @staticmethod
    def _language_score(signal: dict[str, Any]) -> float:
        hindi = signal["devanagari_count"]
        english = signal["english_word_count"]
        total = hindi + english
        if total == 0:
            return 0.5
        return english / total

    def _detect_alternating_pattern(self, signals: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect a repeated two-page Hindi/English pattern from content signals.

        Only question-section pages are considered. The method returns no
        pattern when evidence is insufficient; callers must then use fallback
        routing rather than guessing.
        """
        candidates = [
            (index + 1, signal)
            for index, signal in enumerate(signals)
            if signal["question_marker_count"] > 0
        ]
        if len(candidates) < 4:
            return {"detected": False, "confidence": 0.0, "english_position": None}

        odd_scores = [self._language_score(s) for page, s in candidates if page % 2 == 1]
        even_scores = [self._language_score(s) for page, s in candidates if page % 2 == 0]
        if not odd_scores or not even_scores:
            return {"detected": False, "confidence": 0.0, "english_position": None}

        odd_mean = sum(odd_scores) / len(odd_scores)
        even_mean = sum(even_scores) / len(even_scores)
        separation = abs(odd_mean - even_mean)
        english_position = "odd" if odd_mean > even_mean else "even"

        # Strong separation is required before the pattern is trusted.
        confidence = min(0.99, separation)
        detected = separation >= 0.55
        return {
            "detected": detected,
            "confidence": round(confidence, 3),
            "english_position": english_position if detected else None,
            "odd_english_score": round(odd_mean, 3),
            "even_english_score": round(even_mean, 3),
        }

    def analyze(self, file_path: str) -> AgentResult:
        path = Path(file_path)
        if not path.exists() or path.suffix.lower() != ".pdf":
            raise ValueError("CBSE Board Paper agent requires a PDF file")

        document = fitz.open(str(path))
        signals = [self._page_signal(page) for page in document]
        pattern = self._detect_alternating_pattern(signals)

        pages: list[PageDecision] = []
        for page_number, signal in enumerate(signals, 1):
            is_question_page = signal["question_marker_count"] > 0
            metadata = dict(signal)

            if not is_question_page:
                pages.append(PageDecision(page_number, "cover_or_instruction", "skip", 0.95, metadata))
                continue

            if pattern["detected"]:
                english = (
                    (page_number % 2 == 1 and pattern["english_position"] == "odd")
                    or (page_number % 2 == 0 and pattern["english_position"] == "even")
                )
                if english:
                    pages.append(PageDecision(page_number, "english_question_page", "extract", pattern["confidence"], metadata))
                else:
                    pages.append(PageDecision(page_number, "hindi_duplicate", "skip_duplicate", pattern["confidence"], metadata))
            else:
                # No structural pattern: do not silently guess. This is the
                # safety path for future CBSE layouts that differ from the
                # alternating bilingual family.
                language_score = self._language_score(signal)
                if language_score >= 0.8:
                    pages.append(PageDecision(page_number, "english_question_page", "extract", 0.60, metadata))
                elif language_score <= 0.2:
                    pages.append(PageDecision(page_number, "non_english_question_page", "skip_duplicate", 0.60, metadata))
                else:
                    pages.append(PageDecision(page_number, "uncertain_question_page", "manual_review", 0.50, metadata))

        document.close()
        return AgentResult(
            document_type=self.document_type,
            confidence=pattern["confidence"],
            pages=pages,
            metadata={"agent": self.name, "alternating_pattern": pattern},
        )
