from exam_platform.ingestion.adapters.pdf import PDFAdapter


def test_numeric_continuation_is_not_question_start():
    assert PDFAdapter._question_start("3. 4.") is None


def test_numbered_question_with_text_remains_question_start():
    assert PDFAdapter._question_start("3. Solve 2x + 3y = 11") == (
        "3",
        "Solve 2x + 3y = 11",
    )


def test_bare_numbered_question_marker_remains_supported():
    assert PDFAdapter._question_start("3.") == ("3", "")


def test_duplicate_question_marker_is_not_split():
    assert PDFAdapter._question_start("3.") == ("3", "")
