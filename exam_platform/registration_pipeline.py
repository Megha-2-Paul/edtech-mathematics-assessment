"""Google Form/Sheet registration normalization and controlled enrollment.

The Google Form remains the collection layer. A Google Sheet response export is
reviewed by the founder, and only explicitly enrolled rows are persisted as
Student records in the existing MySQL/Aiven database.

No new database tables are required by this module.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from .models import Student


ALLOWED_SUBJECTS = {"Mathematics", "Applied Mathematics"}
ALLOWED_BOARDS = {"CBSE", "ICSE"}
DEFAULT_ENROLLMENT_STATUSES = {"APPROVED", "ENROLLED", "ACTIVE"}

FIELD_ALIASES = {
    "name": (
        "Student's full name",
        "Student’s full name",
        "Full name",
        "Name",
    ),
    "phone": (
        "WhatsApp number",
        "WhatsApp Number",
        "Phone number",
        "Phone",
    ),
    "email": (
        "Email address",
        "Email Address",
        "Email",
        "Email address (for communication)",
    ),
    "class_level": (
        "Which class are you currently studying in?",
        "Which class are you currently studying in",
        "Class",
        "Class level",
    ),
    "board": (
        "Which board are you studying under?",
        "Which board are you studying under",
        "Board",
    ),
    "subject": (
        "Which Mathematics subject are you studying?",
        "Which Mathematics subject are you studying",
        "Mathematics subject",
        "Subject",
    ),
    "school": (
        "School name",
        "School",
        "Name of your school",
    ),
    "registration_source": (
        "How did you hear about us?",
        "How did you hear about Improvia?",
        "How did you hear",
        "Source",
    ),
    "enrollment_status": (
        "Enrollment Status",
        "Registration Status",
        "Enrollment status",
    ),
}


@dataclass
class RegistrationResult:
    row_number: int
    status: str
    student_id: str | None = None
    message: str = ""


def _clean(value) -> str:
    return str(value or "").strip()


def _normalized_key(value: str) -> str:
    return re.sub(r"\s+", " ", _clean(value)).casefold()


def _find_column(row: Mapping[str, str], field: str) -> str | None:
    normalized = {_normalized_key(k): k for k in row.keys()}
    for alias in FIELD_ALIASES[field]:
        key = normalized.get(_normalized_key(alias))
        if key:
            return key
    return None


def _value(row: Mapping[str, str], field: str) -> str:
    key = _find_column(row, field)
    return _clean(row.get(key)) if key else ""


def normalize_phone(value: str) -> str:
    value = _clean(value)
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return digits


def normalize_email(value: str) -> str:
    return _clean(value).casefold()


def normalize_board(value: str) -> str:
    value = _clean(value).upper()
    if value == "CBSE":
        return "CBSE"
    if value == "ICSE":
        return "ICSE"
    return value


def normalize_subject(value: str) -> str:
    value = _clean(value).casefold()
    if value == "mathematics":
        return "Mathematics"
    if value == "applied mathematics":
        return "Applied Mathematics"
    return _clean(value)


def normalize_class(value: str) -> int | None:
    match = re.search(r"\d{1,2}", _clean(value))
    return int(match.group()) if match else None


def extract_registration(row: Mapping[str, str], row_number: int) -> tuple[Student | None, str | None]:
    name = _value(row, "name")
    email = normalize_email(_value(row, "email"))
    phone = normalize_phone(_value(row, "phone"))
    board = normalize_board(_value(row, "board"))
    subject = normalize_subject(_value(row, "subject"))
    class_level = normalize_class(_value(row, "class_level"))

    missing = []
    if not name:
        missing.append("name")
    if not email and not phone:
        missing.append("email or phone")
    if class_level is None:
        missing.append("class")
    if board not in ALLOWED_BOARDS:
        missing.append("board")
    if subject not in ALLOWED_SUBJECTS:
        missing.append("subject")
    if missing:
        return None, f"Invalid registration: missing/invalid {', '.join(missing)}."

    student = Student(
        student_id="",
        name=name,
        email=email,
        phone=phone or None,
        class_level=class_level,
        board=board,
        subject=subject,
        school=_value(row, "school") or None,
        registration_date=date.today().isoformat(),
        registration_source=_value(row, "registration_source") or "google_form",
        status="active",
    )
    return student, None


def _existing_student_ids(email: str, phone: str) -> set[str]:
    from sqlalchemy import text
    from database import engine

    ids: set[str] = set()
    with engine.connect() as db:
        if email:
            rows = db.execute(
                text("SELECT student_id FROM students WHERE LOWER(email)=:email"),
                {"email": email},
            ).scalars().all()
            ids.update(rows)
        if phone:
            rows = db.execute(
                text("SELECT student_id FROM students WHERE phone=:phone"),
                {"phone": phone},
            ).scalars().all()
            ids.update(rows)
    return ids


def _new_student_id() -> str:
    return f"STU{uuid.uuid4().hex[:10].upper()}"


def enroll_student(student: Student) -> Student:
    """Create or update a permanent Student using email/phone identity matching.

    This is deliberately called only for a row that has passed the enrollment
    gate. It writes to the existing MySQL database; with DATABASE_URL pointing
    at Aiven, that is the production Student record.
    """
    ids = _existing_student_ids(student.email, normalize_phone(student.phone or ""))
    if len(ids) > 1:
        raise ValueError(
            "Registration identity conflict: email and phone match different Student_IDs."
        )

    if ids:
        student.student_id = next(iter(ids))
    else:
        student.student_id = _new_student_id()

    from .storage import storage

    storage.register_student(student)
    return student


def read_csv_rows(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")
    return [dict(row) for row in reader]


def fetch_google_sheet_csv(sheet_url: str) -> str:
    """Fetch a Google Sheet CSV export.

    The source sheet must be accessible to the credentials/network making this
    request. This MVP intentionally does not embed Google OAuth credentials.
    For a private sheet, export/download the reviewed sheet CSV and pass it to
    the importer instead of making student data public.
    """
    parsed = urlparse(sheet_url)
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", parsed.path)
    if not match:
        raise ValueError("Could not find a Google Spreadsheet ID in the URL.")

    sheet_id = match.group(1)
    query = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    gid = (query.get("gid") or fragment.get("gid") or ["0"])[0]
    export_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        f"?format=csv&gid={gid}"
    )
    request = Request(export_url, headers={"User-Agent": "Improvia-registration-import/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def import_enrolled_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    enrollment_statuses: set[str] | None = None,
    dry_run: bool = True,
) -> list[RegistrationResult]:
    statuses = {
        _clean(value).upper()
        for value in (enrollment_statuses or DEFAULT_ENROLLMENT_STATUSES)
    }
    results: list[RegistrationResult] = []

    for row_number, row in enumerate(rows, start=2):
        raw_status = _value(row, "enrollment_status").upper()

        if not raw_status:
            results.append(
                RegistrationResult(
                    row_number,
                    "PENDING",
                    message="No Enrollment Status; not written to database.",
                )
            )
            continue

        if raw_status not in statuses:
            results.append(
                RegistrationResult(
                    row_number,
                    "SKIPPED",
                    message=f"Enrollment Status={raw_status!r}; not written.",
                )
            )
            continue

        student, error = extract_registration(row, row_number)
        if error:
            results.append(RegistrationResult(row_number, "ERROR", message=error))
            continue

        if dry_run:
            results.append(
                RegistrationResult(
                    row_number,
                    "READY",
                    message=f"{student.name} is valid for enrollment.",
                )
            )
            continue

        try:
            student = enroll_student(student)
            results.append(
                RegistrationResult(
                    row_number,
                    "ENROLLED",
                    student_id=student.student_id,
                    message=f"{student.name} enrolled successfully.",
                )
            )
        except Exception as exc:
            results.append(
                RegistrationResult(
                    row_number,
                    "ERROR",
                    message=str(exc),
                )
            )

    return results
