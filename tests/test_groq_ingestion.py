from __future__ import annotations

import json
from pathlib import Path

import pytest

from question_bank.extraction.groq_provider import (
    GroqExtractionError,
    GroqProvider,
)
from question_bank.ingest_groq import extract_pdf_text_pages, run_extraction


def test_provider_requires_api_key_without_printing_or_logging_secret(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(GroqExtractionError, match="GROQ_API_KEY is not set"):
        GroqProvider(api_key=" ")


def test_provider_uses_json_mode_and_overrides_untrusted_provenance(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "questions": [{
                                "question_number": "1",
                                "question_text": "Solve x² - 5x + 6 = 0.",
                                "marks": 3,
                                "source_page": 999,
                                "extraction_warnings": [],
                            }],
                            "source": {"source_file": "attacker.pdf"},
                        })
                    }
                }]
            }).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("question_bank.extraction.groq_provider.urlopen", fake_urlopen)
    provider = GroqProvider(api_key="test-secret", model="test-model")
    payload = provider.extract_page(
        "Question 1: Solve x² - 5x + 6 = 0. [3]",
        source_file="sample.pdf",
        source_page=2,
        board="ICSE",
        class_level=10,
    )

    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["model"] == "test-model"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert payload["source"]["source_file"] == "sample.pdf"
    assert payload["questions"][0]["source_page"] == 2
    assert payload["questions"][0]["source_pages"] == [2]
    assert payload["extraction_provider"] == "groq"


def test_provider_rejects_invalid_questions_shape(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": '{"unexpected": []}'}}]
            }).encode()

    monkeypatch.setattr("question_bank.extraction.groq_provider.urlopen", lambda *a, **k: FakeResponse())
    provider = GroqProvider(api_key="test-secret")
    with pytest.raises(GroqExtractionError, match="questions array"):
        provider.extract_page("Q1. Find x.", source_file="sample.pdf", source_page=1)


def test_extract_pdf_text_pages_preserves_page_numbers(tmp_path):
    import fitz

    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    for text in ("Question 1. Find x.", "Question 2. Find y."):
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(pdf_path)
    document.close()

    assert extract_pdf_text_pages(pdf_path, max_pages=1) == [(1, "Question 1. Find x.")]


def test_extract_pdf_text_pages_rejects_scanned_or_empty_page(tmp_path):
    import fitz

    pdf_path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    with pytest.raises(ValueError, match="no extractable text"):
        extract_pdf_text_pages(pdf_path, max_pages=1)


def test_run_extraction_saves_review_only_payload_and_uses_shared_importer(tmp_path):
    import fitz

    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Question 1. Solve x + 2 = 5. [2]")
    document.save(pdf_path)
    document.close()

    class FakeProvider:
        model = "test-model"

        def extract_page(self, page_text, **kwargs):
            return {
                "questions": [{
                    "question_number": "1",
                    "question_text": "Solve x + 2 = 5.",
                    "marks": 2,
                    "question_type": "saq",
                    "source_page": kwargs["source_page"],
                    "source_pages": [kwargs["source_page"]],
                    "extraction_warnings": [],
                }]
            }

    output_path = tmp_path / "out" / "candidates.json"
    summary = run_extraction(
        pdf_path,
        output_path=output_path,
        max_pages=1,
        provider=FakeProvider(),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["questions"][0]["source_page"] == 1
    assert payload["extraction_provider"] == "groq"
    assert summary["extracted_questions"] == 1
    assert summary["publication"].startswith("NOT PUBLISHED")
    assert summary["output_path"] == str(output_path)
