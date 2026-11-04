import pytest

from exam_platform.evaluation import _validate_marks


@pytest.mark.parametrize(
    ("marks", "maximum", "expected"),
    [
        ("0", 5, 0.0),
        ("0.5", 5, 0.5),
        ("2.5", 5, 2.5),
        ("5", 5, 5.0),
        ("3.5", 3.5, 3.5),
    ],
)
def test_valid_marks_are_accepted(marks, maximum, expected):
    assert _validate_marks(marks, maximum) == expected


@pytest.mark.parametrize(
    ("marks", "maximum"),
    [
        ("", 5),
        ("   ", 5),
        ("abc", 5),
        ("-0.5", 5),
        ("5.5", 5),
        ("NaN", 5),
        ("Infinity", 5),
        ("-Infinity", 5),
        ("0.25", 5),
    ],
)
def test_invalid_marks_are_rejected(marks, maximum):
    with pytest.raises(ValueError):
        _validate_marks(marks, maximum)


def test_invalid_maximum_is_rejected():
    with pytest.raises(ValueError):
        _validate_marks("1", "NaN")
