from exam_platform.ingestion.adapters.url import URLAdapter
from exam_platform.ingestion.models import SourceDocument, SourceType


FIXTURE_HTML = """
<html><body>
<nav>Mathematics Question Bank</nav>
<h2>Quadratic Equations</h2>
<div>1. If the roots of x² - 5x + 6 = 0 are α and β, find α + β. [2 Marks]</div>
<div>2. Which is a root of x² - 9 = 0?</div>
<div>(A) 2</div><div>(B) 3</div><div>(C) 4</div><div>(D) 9</div>
<script>3. This must not be extracted.</script>
</body></html>
"""


def test_visible_blocks_ignore_scripts():
    blocks = URLAdapter._visible_blocks(FIXTURE_HTML)
    assert "3. This must not be extracted." not in blocks
    assert "Mathematics Question Bank" in blocks


def test_extract_numbered_questions_and_metadata():
    questions = URLAdapter._parse_questions(
        URLAdapter._visible_blocks(FIXTURE_HTML), "shaalaa-test"
    )

    assert len(questions) == 2
    assert questions[0].raw_text.startswith("If the roots")
    assert questions[0].raw_marks == 2.0
    assert questions[0].metadata["chapter_hint"] == "Quadratic Equations"
    assert questions[1].raw_options == ["2", "3", "4", "9"]
    assert questions[1].metadata["question_type"] == "mcq"
    assert questions[1].metadata["needs_human_review"] is True


def test_url_source_contract():
    source = SourceDocument(
        source_id="shaalaa-test",
        source_type=SourceType.URL.value,
        url="https://example.com/questions",
    )
    adapter = URLAdapter(source)
    assert adapter.source is source


def test_reject_non_http_url():
    source = SourceDocument(
        source_id="bad",
        source_type=SourceType.URL.value,
        url="file:///tmp/questions.html",
    )
    try:
        URLAdapter(source)
    except ValueError as exc:
        assert "http(s)" in str(exc)
    else:
        raise AssertionError("Expected invalid URL to be rejected")
