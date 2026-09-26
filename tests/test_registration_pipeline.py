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
