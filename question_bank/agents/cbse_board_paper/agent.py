"""CBSE Board Paper agent.

CBSE board papers handled by this agent use the known bilingual layout:
page 1 is the cover/instruction page, followed by alternating Hindi and
English question pages. The format is intentionally explicit rather than
inferred from text similarity. A small language sanity check protects
against silently applying the rule to an unexpected document layout.
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
QUESTION_RE = re.compile(r"(?:^|\s)(?:Q\.?\s*)?\d{1,2}\s*[.)]", re.I)

# Known layout for the CBSE bilingual board-paper family supported by this
# agent. This is a document-format rule, not a rule for one specific PDF.
COVER_PAGE = 1
FIRST_QUESTION_PAGE = 2
HINDI_PAGE_PARITY = 0  # even-numbered pages
ENGLISH_PAGE_PARITY = 1  # odd-numbered pages


class CBSEBoardPaperAgent:
    """Route pages belonging to the supported CBSE board-paper family."""

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
        """Return an English-vs-Hindi signal in [0, 1]."""
        hindi = signal["devanagari_count"]
        english = signal["english_word_count"]
        total = hindi + english
        if total == 0:
            return 0.5
        return english / total

    def _validate_known_layout(self, signals: list[dict[str, Any]]) -> dict[str, Any]:
        """Sanity-check the known CBSE layout before applying it.

        The routing rule itself is fixed: page 1 is the cover, even pages are
        Hindi duplicates, and odd pages from page 3 onward are English. The
        sanity check only determines whether it is safe to apply that rule.
        """
        if len(signals) < FIRST_QUESTION_PAGE + 1:
            return {
                "validated": False,
                "confidence": 0.0,
                "reason": "document_too_short_for_bilingual_layout",
            }

        # Inspect the first few Hindi/English pairs. Do not require perfect
        # text-layer extraction because some PDFs have incomplete language text.
        pair_end = min(len(signals), 8)
        pairs_checked = 0
        language_consistent = 0

        for page_number in range(FIRST_QUESTION_PAGE, pair_end + 1):
            if page_number % 2 != 0:
                continue
            english_page = page_number + 1
            if english_page > len(signals):
                break

            hindi_signal = signals[page_number - 1]
            english_signal = signals[english_page - 1]
            hindi_score = self._language_score(hindi_signal)
            english_score = self._language_score(english_signal)
            pairs_checked += 1

            if hindi_score <= 0.5 and english_score >= 0.5:
                language_consistent += 1

        if pairs_checked == 0:
            return {
                "validated": False,
                "confidence": 0.0,
                "reason": "no_question_pairs_available",
            }

        consistency = language_consistent / pairs_checked
        validated = consistency >= 0.75
        confidence = 0.95 if consistency == 1.0 else 0.85 if validated else 0.50

        return {
            "validated": validated,
            "confidence": confidence,
            "reason": "known_cbse_bilingual_layout" if validated else "language_sanity_check_failed",
            "pairs_checked": pairs_checked,
            "language_consistency": round(consistency, 3),
            "cover_page": COVER_PAGE,
            "hindi_page_parity": "even",
            "english_page_parity": "odd",
        }

    def analyze(self, file_path: str) -> AgentResult:
        path = Path(file_path)
        if not path.exists() or path.suffix.lower() != ".pdf":
            raise ValueError("CBSE Board Paper agent requires a PDF file")

        with fitz.open(str(path)) as document:
            signals = [self._page_signal(page) for page in document]

        layout = self._validate_known_layout(signals)
        pages: list[PageDecision] = []

        if not layout["validated"]:
            # Do not fall back to risky page-by-page guessing. An unexpected
            # CBSE layout must be explicitly reviewed before extraction.
            for page_number, signal in enumerate(signals, 1):
                metadata = dict(signal)
                metadata["layout_validation"] = layout
                pages.append(
                    PageDecision(
                        page_number,
                        "manual_review_required",
                        "manual_review",
                        layout["confidence"],
                        metadata,
                    )
                )

            return AgentResult(
                document_type=self.document_type,
                confidence=layout["confidence"],
                pages=pages,
                metadata={"agent": self.name, "layout": layout},
            )

        for page_number, signal in enumerate(signals, 1):
            metadata = dict(signal)
            metadata["layout_rule"] = "page1_cover_even_hindi_odd_english"
            metadata["layout_validation"] = layout

            if page_number == COVER_PAGE:
                pages.append(
                    PageDecision(
                        page_number,
                        "cover_or_instruction",
                        "skip",
                        layout["confidence"],
                        metadata,
                    )
                )
            elif page_number % 2 == HINDI_PAGE_PARITY:
                pages.append(
                    PageDecision(
                        page_number,
                        "hindi_duplicate",
                        "skip_duplicate",
                        layout["confidence"],
                        metadata,
                    )
                )
            else:
                pages.append(
                    PageDecision(
                        page_number,
                        "english_question_page",
                        "extract",
                        layout["confidence"],
                        metadata,
                    )
                )

        return AgentResult(
            document_type=self.document_type,
            confidence=layout["confidence"],
            pages=pages,
            metadata={"agent": self.name, "layout": layout},
        )
