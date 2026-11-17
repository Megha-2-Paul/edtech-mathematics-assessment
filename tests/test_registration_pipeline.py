import pytest

import exam_platform.registration_pipeline as pipeline
from exam_platform.registration_pipeline import (
    extract_registration,
    import_enrolled_rows,
    normalize_class,
    normalize_phone,
    normalize_subject,
)


def base_row(**overrides):
    row = {
        "Student's full name": "Aditi Sharma",
        "WhatsApp number": "+91 98765 43210",
        "Email address": "Aditi@Example.com",
        "Which class are you currently studying in?": "Class 10",
        "Which board are you studying under?": "CBSE",
        "Which Mathematics subject are you studying?": "Mathematics",
        "Enrollment Status": "APPROVED",
    }
    row.update(overrides)
    return row


def test_normalization():
    assert normalize_phone("+91 98765-43210") == "9876543210"
    assert normalize_subject(" applied mathematics ") == "Applied Mathematics"
    assert normalize_class("Class 12") == 12


def test_extracts_actual_google_form_fields():
    student, error = extract_registration(base_row(), 2)
    assert error is None
    assert student.name == "Aditi Sharma"
    assert student.email == "aditi@example.com"
    assert student.phone == "9876543210"
    assert student.class_level == 10
    assert student.board == "CBSE"
    assert student.subject == "Mathematics"


def test_invalid_subject_is_rejected():
    student, error = extract_registration(
        base_row(**{"Which Mathematics subject are you studying?": "Physics"}), 2
    )
    assert student is None
    assert "subject" in error


def test_unapproved_rows_never_write():
    results = import_enrolled_rows(
        [base_row(**{"Enrollment Status": "PENDING"})],
        dry_run=False,
    )
    assert results[0].status == "SKIPPED"


def test_missing_enrollment_status_never_writes():
    row = base_row()
    del row["Enrollment Status"]
    results = import_enrolled_rows([row], dry_run=False)
    assert results[0].status == "PENDING"


def test_fetch_google_sheet_csv_accepts_valid_google_url(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"name,email\nAditi,aditi@example.com\n"

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(pipeline, "urlopen", fake_urlopen)

    result = pipeline.fetch_google_sheet_csv(
        "https://docs.google.com/spreadsheets/d/abc_123/edit?gid=456"
    )

    assert result == "name,email\nAditi,aditi@example.com\n"
    assert captured["url"] == (
        "https://docs.google.com/spreadsheets/d/abc_123/export?"
        "format=csv&gid=456"
    )
    assert captured["timeout"] == 30


def test_fetch_google_sheet_csv_accepts_fragment_gid(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"data"

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(pipeline, "urlopen", fake_urlopen)

    pipeline.fetch_google_sheet_csv(
        "https://docs.google.com/spreadsheets/d/abc123/edit#gid=789"
    )

    assert captured["url"].endswith("format=csv&gid=789")


@pytest.mark.parametrize(
    "url",
    [
        "http://docs.google.com/spreadsheets/d/abc123/edit",
        "https://evil.example/spreadsheets/d/abc123/edit",
        "https://docs.google.com.evil.example/spreadsheets/d/abc123/edit",
        "https://user:password@docs.google.com/spreadsheets/d/abc123/edit",
        "https://docs.google.com:8443/spreadsheets/d/abc123/edit",
        "https://docs.google.com/spreadsheets/d/abc123/edit?gid=abc",
        "https://docs.google.com/spreadsheets/d/invalid.id/edit",
        "https://docs.google.com/other/path",
        "https://[invalid-host/spreadsheets/d/abc123/edit",
    ],
)
def test_fetch_google_sheet_csv_rejects_invalid_urls(monkeypatch, url):
    def unexpected_request(*args, **kwargs):
        pytest.fail("HTTP request must not occur for an invalid URL.")

    monkeypatch.setattr(pipeline, "urlopen", unexpected_request)

    with pytest.raises(ValueError):
        pipeline.fetch_google_sheet_csv(url)


def test_fetch_google_sheet_csv_defaults_to_first_worksheet(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"data"

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(pipeline, "urlopen", fake_urlopen)

    pipeline.fetch_google_sheet_csv(
        "https://docs.google.com/spreadsheets/d/abc123/edit"
    )

    assert captured["url"].endswith("format=csv&gid=0")
