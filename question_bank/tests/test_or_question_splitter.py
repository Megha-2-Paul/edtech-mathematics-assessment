from question_bank.extraction.or_question_splitter import is_explicit_or_question, split_or_parts


def test_splits_explicit_a_b_or_question():
    text = "(a) First method. OR (b) Second method."
    parts = [
        {"part_identifier": "a", "part_text": "First method.", "marks": 3},
        {"part_identifier": "b", "part_text": "Second method.", "marks": 3},
    ]
    assert is_explicit_or_question(text, parts)
    result = split_or_parts(text, parts)
    assert [x["part_identifier"] for x in result] == ["a", "b"]
    assert [x["question_text"] for x in result] == ["First method.", "Second method."]


def test_does_not_split_i_ii_subquestions_without_or():
    text = "Find the probability of (i) one event and (ii) another event."
    parts = [
        {"part_identifier": "i", "part_text": "one event", "marks": 1},
        {"part_identifier": "ii", "part_text": "another event", "marks": 1},
    ]
    assert not is_explicit_or_question(text, parts)
    assert split_or_parts(text, parts) == []


def test_does_not_flatten_case_study_with_nested_or():
    text = "Answer the following. (i) First. (ii) Second. (iii)(a) Third. OR (iii)(b) Fourth."
    parts = [
        {"part_identifier": "i", "part_text": "First", "marks": 1},
        {"part_identifier": "ii", "part_text": "Second", "marks": 1},
        {"part_identifier": "iii(a)", "part_text": "Third", "marks": 2},
        {"part_identifier": "iii(b)", "part_text": "Fourth", "marks": 2},
    ]
    assert not is_explicit_or_question(text, parts)
    assert split_or_parts(text, parts) == []


def test_does_not_split_a_b_when_or_is_missing():
    text = "(a) Part one. (b) Part two."
    parts = [
        {"part_identifier": "a", "part_text": "Part one"},
        {"part_identifier": "b", "part_text": "Part two"},
    ]
    assert not is_explicit_or_question(text, parts)
    assert split_or_parts(text, parts) == []
