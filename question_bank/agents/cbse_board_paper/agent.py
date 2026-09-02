"""CBSE Board Paper agent.

Document-level routing is intentionally the primary language strategy. For
bilingual CBSE papers that follow an alternating Hindi/English layout, the
agent detects the repeated two-page structure once and routes pages from that
pattern instead of independently classifying every page. Page-level signals
remain safeguards and fallback evidence.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from question_bank.agents.base import AgentResult, DocumentAgent, PageDecision

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
ENGLISH_WORD_RE = re.compile(
    r"\b(?:the|question|section|marks|find|solve|calculate|prove|show|answer|choose|given|following)\b",
    re.I,
)
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

    @staticmethod
    def _pair_similarity(first: dict[str, Any], second: dict[str, Any]) -> float:
        """Estimate whether adjacent pages have the same question-page structure.

        Bilingual duplicate pages normally contain the same question ranges and
        therefore have broadly similar text/question-marker density, even when
        one script is not extractable from the PDF text layer.
        """
        text_a = max(first["text_length"], 1)
        text_b = max(second["text_length"], 1)
        length_similarity = min(text_a, text_b) / max(text_a, text_b)

        markers_a = first["question_marker_count"]
        markers_b = second["question_marker_count"]
        if max(markers_a, markers_b) == 0:
            marker_similarity = 0.0
        else:
            marker_similarity = min(markers_a, markers_b) / max(markers_a, markers_b)

        return 0.6 * length_similarity + 0.4 * marker_similarity

    def _detect_alternating_pattern(self, signals: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect a repeated bilingual two-page pattern at document level.

        The detector deliberately does not assume that odd pages are English.
        It first looks for repeated adjacent page pairs, then determines which
        position in each pair is English using whatever language evidence is
        available. This is important for scanned PDFs whose Hindi text may not
        be represented as Unicode Devanagari in the PDF text layer.
        """
        if len(signals) < 5:
            return {"detected": False, "confidence": 0.0, "english_position": None}

        # Page 1 is commonly a cover/instruction page. Do not use it to infer
        # the bilingual pattern; the repeating body starts from page 2 onward.
        body = signals[1:]
        pairs = [
            (body[index], body[index + 1])
            for index in range(0, len(body) - 1, 2)
        ]
        if len(pairs) < 2:
            return {"detected": False, "confidence": 0.0, "english_position": None}

        pair_scores = [self._pair_similarity(first, second) for first, second in pairs]
        structural_score = sum(pair_scores) / len(pair_scores)

        # Determine language position independently of pair structure. A page
        # with recognizable English words is strong evidence for English. A
        # page with recognizable Devanagari is strong evidence for Hindi. If
        # both scripts are unavailable, the pair remains uncertain.
        first_position_scores = []
        second_position_scores = []
        for first, second in pairs:
            first_position_scores.append(self._language_score(first))
            second_position_scores.append(self._language_score(second))

        first_mean = sum(first_position_scores) / len(first_position_scores)
        second_mean = sum(second_position_scores) / len(second_position_scores)
        separation = abs(first_mean - second_mean)

        if first_mean > second_mean:
            english_position = "first"
        elif second_mean > first_mean:
            english_position = "second"
        else:
            english_position = None

        # When one script is not extractable, _language_score returns 0.5.
        # Therefore a clear English/non-English contrast can still identify
        # the position. Require both structural repetition and language
        # separation before trusting the pattern.
        detected = structural_score >= 0.65 and separation >= 0.35
        confidence = min(0.99, 0.55 * structural_score + 0.45 * separation)

        return {
            "detected": detected,
            "confidence": round(confidence, 3) if detected else round(confidence, 3),
            "english_position": english_position if detected else None,
            "pair_count": len(pairs),
            "structural_score": round(structural_score, 3),
            "language_separation": round(separation, 3),
            "first_position_english_score": round(first_mean, 3),
            "second_position_english_score": round(second_mean, 3),
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
            metadata = dict(signal)

            # The first page of this document family is usually a cover or
            # instructions page. Keep this as a content-based safety check,
            # rather than using it to infer the bilingual page pattern.
            if page_number == 1 and pattern["detected"]:
                pages.append(
                    PageDecision(
                        page_number,
                        "cover_or_instruction",
                        "skip",
                        max(0.90, pattern["confidence"]),
                        metadata,
                    )
                )
                continue

            if pattern["detected"]:
                # Body starts at page 2. "first" means page 2, 4, 6...;
                # "second" means page 3, 5, 7....
                position_in_pair = "first" if page_number % 2 == 0 else "second"
                english = position_in_pair == pattern["english_position"]
                if english:
                    pages.append(
                        PageDecision(
                            page_number,
                            "english_question_page",
                            "extract",
                            pattern["confidence"],
                            metadata,
                        )
                    )
                else:
                    pages.append(
                        PageDecision(
                            page_number,
                            "hindi_duplicate",
                            "skip_duplicate",
                            pattern["confidence"],
                            metadata,
                        )
                    )
                continue

            # No reliable document-level pattern: do not silently guess. This
            # is the safety path for future CBSE layouts that differ from the
            # alternating bilingual family.
            is_question_page = signal["question_marker_count"] > 0
            if not is_question_page:
                pages.append(
                    PageDecision(page_number, "cover_or_instruction", "skip", 0.95, metadata)
                )
                continue

            language_score = self._language_score(signal)
            if language_score >= 0.8:
                pages.append(
                    PageDecision(page_number, "english_question_page", "extract", 0.60, metadata)
                )
            elif language_score <= 0.2:
                pages.append(
                    PageDecision(page_number, "non_english_question_page", "skip_duplicate", 0.60, metadata)
                )
            else:
                pages.append(
                    PageDecision(page_number, "uncertain_question_page", "manual_review", 0.50, metadata)
                )

        document.close()
        return AgentResult(
            document_type=self.document_type,
            confidence=pattern["confidence"],
            pages=pages,
            metadata={"agent": self.name, "alternating_pattern": pattern},
        )
