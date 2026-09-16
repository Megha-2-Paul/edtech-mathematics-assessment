from exam_platform.ingestion.adapters.shaalaa import ShaalaaPageParser
from exam_platform.ingestion.models import SourceDocument, SourceType


SHAALAA_FIXTURE = """
<html><body>
<nav>Question Bank Textbook Solutions Login</nav>
<h1>ICSE Class 10 Mathematics Question Bank</h1>
<div>Subjects</div>
<div>Topics</div>
<div>prev 1 to 20 of 2423 next</div>
<div>Mathematics</div>
<div>Jaya borrowed Rs. 50,000 for 2 years. Find the amount she must pay.</div>
<div>[1] Compound Interest</div>
<a>VIEW SOLUTION</a>
<div>Chapter: [1] Compound Interest</div>
<div>Concept: undefined &gt;&gt; undefined</div>
<div>If (3a + 2b) : (5a + 3b) = 18 : 29. Find a : b</div>
<div>[6] Ratio and Proportion</div>
<a>VIEW SOLUTION</a>
<div>Chapter: [6] Ratio and Proportion</div>
<div>Concept: undefined &gt;&gt; undefined</div>
<div>In the figure below, prove the required result.</div>
<div>Image</div>
<div>[15] Constructions</div>
<div>Chapter: [15] Constructions</div>
<div>Footer navigation and advertisements</div>
</body></html>
"""


def test_shaalaa_parser_splits_questions_and_ignores_navigation():
    blocks = __import__(
        "exam_platform.ingestion.adapters.url", fromlist=["URLAdapter"]
    ).URLAdapter._visible_blocks(SHAALAA_FIXTURE)
    questions = ShaalaaPageParser._parse_blocks(blocks, "shaalaa-test")

    assert len(questions) == 3
    assert questions[0].raw_text.startswith("Jaya borrowed")
    assert questions[1].raw_text.startswith("If (3a + 2b)")
    assert "Footer navigation" not in questions[-1].raw_text


def test_shaalaa_topic_index_is_not_treated_as_marks():
    blocks = __import__(
        "exam_platform.ingestion.adapters.url", fromlist=["URLAdapter"]
    ).URLAdapter._visible_blocks(SHAALAA_FIXTURE)
    questions = ShaalaaPageParser._parse_blocks(blocks, "shaalaa-test")

    assert questions[0].raw_marks is None
    assert questions[0].metadata["marks_source"] == "not_explicitly_available"
    assert questions[0].metadata["chapter_hint"] == "Compound Interest"
    assert questions[0].metadata["shaalaa_topic_index"] == 1


def test_shaalaa_image_is_flagged_for_review():
    blocks = __import__(
        "exam_platform.ingestion.adapters.url", fromlist=["URLAdapter"]
    ).URLAdapter._visible_blocks(SHAALAA_FIXTURE)
    questions = ShaalaaPageParser._parse_blocks(blocks, "shaalaa-test")

    assert questions[2].metadata["contains_image"] is True
    assert questions[2].extraction_confidence < questions[0].extraction_confidence
    assert questions[2].metadata["needs_human_review"] is True


def test_shaalaa_parser_rejects_non_shaalaa_hosts():
    source = SourceDocument(
        source_id="bad",
        source_type=SourceType.URL.value,
        url="https://example.com/questions",
    )
    try:
        ShaalaaPageParser(source)
    except ValueError as exc:
        assert "shaalaa.com" in str(exc).lower()
    else:
        raise AssertionError("Expected non-Shaalaa URL to be rejected")
