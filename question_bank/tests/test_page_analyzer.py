"""Unit tests for render-first local page routing."""

from question_bank.page_analyzer import (
    _classify_and_route,
    _image_similarity,
    analyze_page,
)


class FakePage:
    def __init__(self, text: str, image_count: int = 0):
        self._text = text
        self._images = [object()] * image_count

    def extract_text(self):
        return self._text

    @property
    def images(self):
        return self._images


def test_english_question_page_is_detected():
    result = analyze_page(
        FakePage(
            "SECTION B\nQuestion numbers 7 to 10 carry 3 marks each.\n"
            "Find the height.\nFigure 1"
        ),
        5,
    )
    assert result["language"] == "english"
    assert result["question_start"] == 7
    assert result["question_end"] == 10
    assert result["is_question_page"] is True
    assert result["has_figures"] is True


def test_question_number_is_detected_when_not_at_line_start():
    result = analyze_page(
        FakePage("The following is given. 14. Find the modal age of the policy holders."),
        11,
    )
    assert result["question_start"] == 14
    assert result["question_end"] == 14
    assert result["is_question_page"] is True


def test_non_question_cover_is_not_classified_as_question_page():
    result = analyze_page(FakePage("Candidates must write the Q.P. Code on the title page."), 1)
    assert result["is_question_page"] is False
    assert result["routing"] == "skip"


def test_non_english_question_page_is_manual_review_candidate():
    result = analyze_page(FakePage("प्रश्न 1. निम्नलिखित को हल कीजिए।"), 2)
    assert result["is_question_page"] is True
    assert result["language"] == "non_english"
    assert result["routing"] == "extract_vision"
    _classify_and_route([result])
    assert result["routing"] == "manual_review"
    assert result["needs_visual_review"] is True


def test_identical_rendered_fingerprints_have_full_similarity():
    fingerprint = bytes(range(64))
    assert _image_similarity(fingerprint, fingerprint) == 1.0


def test_adjacent_bilingual_pages_route_to_english_only():
    hindi = analyze_page(
        FakePage("प्रश्न 1. निम्नलिखित हल कीजिए। 2. उत्तर दीजिए."), 2
    )
    english = analyze_page(
        FakePage("Question 1. Solve the following. 2. Give the answer."), 3
    )
    # Simulate a high structural match from the render stage. This isolates
    # duplicate routing from the PDF renderer itself.
    hindi["image_fingerprint"] = bytes([10]) * 64
    english["image_fingerprint"] = bytes([10]) * 64
    _classify_and_route([hindi, english])
    assert hindi["routing"] == "skip_duplicate"
    assert hindi["paired_english_page"] == 3
    assert english["routing"] == "extract_vision"
    assert hindi["duplicate_score"] >= 0.65
