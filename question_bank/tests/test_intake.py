"""Small smoke tests for source-PDF intake."""
from pathlib import Path


def test_source_id_is_stable_for_same_file(tmp_path: Path):
    from question_bank.intake import _source_id

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"placeholder")
    first = _source_id(pdf)
    second = _source_id(pdf)
    assert first == second
    assert first.startswith("SRC-")
