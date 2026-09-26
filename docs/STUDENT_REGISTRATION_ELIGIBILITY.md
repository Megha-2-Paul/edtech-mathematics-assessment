# Student Registration and Assessment Eligibility

## Registration fields used by the assessment engine

The Google Form already collects these values:

| Google Form question | Student field | Required for eligibility |
|---|---|---|
| Student's full name | `name` | Yes |
| WhatsApp number | `phone` | No |
| Email address | `email` | No |
| Which class are you currently studying in? | `class_level` | Yes |
| Which board are you studying under? | `board` | Yes |
| Which Mathematics subject are you studying? | `subject` | Yes |

The accepted subject values are exactly:

- `Mathematics`
- `Applied Mathematics`

Existing/guest student records may have a NULL subject until registration is reviewed.

## Eligibility rule

A student can access an assessment only when all three match:

```text
student.board       == test.board
student.class_level == test.class_level
student.subject     == test.subject
```

The check is applied twice:

1. `GET /tests` — ineligible assessments are not listed.
2. `POST /api/test/<test_id>/start` — direct attempts are rejected with HTTP 403.

The instructions page also applies the same check, so a user cannot bypass the listing by opening an assessment URL directly.

## Registration persistence

`Student.subject` is persisted in the existing `students` table. The additive migration is:

`question_bank/migrations/004_student_registration_subject.sql`

The runtime schema bootstrap in `database.py` also adds the column for fresh/existing environments.

The storage layer exposes `register_student(student)` for a reviewed registration record. It accepts only CBSE/ICSE plus Mathematics/Applied Mathematics and requires class level.

## Actual Google Form → Google Sheet → Student/Aiven pipeline

The repository now has a controlled registration importer in:

- `exam_platform/registration_pipeline.py`
- `scripts/import_google_registrations.py`
- `tests/test_registration_pipeline.py`

The pipeline is deliberately **enrollment-gated**:

```text
Google Form
   ↓
Google Form response Sheet
   ↓
Founder reviews the row
   ↓
Set "Enrollment Status" = APPROVED / ENROLLED / ACTIVE
   ↓
Importer dry-run
   ↓
Review import audit
   ↓
Importer --write
   ↓
Existing students table
   ↓
Aiven (when DATABASE_URL points to Aiven)
   ↓
Student_ID becomes eligible for matching assessments
```

### Important: no new database table is introduced

This pipeline writes to the existing `students` table only. It does not add a registration table, subscription table, or duplicate student database.

### Identity matching

When an enrolled row is written:

1. Email is normalized and checked first.
2. Phone is normalized and checked next.
3. If both identify the same existing student, that permanent `Student_ID` is reused.
4. If neither identifies an existing student, a new permanent `STU...` ID is generated.
5. If email and phone point to different students, the row is rejected as an identity conflict rather than silently creating a duplicate.

This fixes the MVP's earlier problem where a browser session could create a random guest ID that was not tied to the registration record.

### Google Sheet requirement

Add a manual column named **`Enrollment Status`** to the response Sheet. The Google Form questions themselves do not need to change. Only rows explicitly marked `APPROVED`, `ENROLLED`, or `ACTIVE` are eligible for database writes.

The importer accepts the exact Form fields already collected, including:

- `Student's full name`
- `WhatsApp number`
- `Email address`
- `Which class are you currently studying in?`
- `Which board are you studying under?`
- `Which Mathematics subject are you studying?`

Additional survey/diagnostic columns remain in Google Sheets and are not forced into the core `students` record.

### Import commands

Dry-run a CSV export first:

```bash
python scripts/import_google_registrations.py --csv registrations.csv
```

After reviewing the generated `registration_import_results.csv`:

```bash
python scripts/import_google_registrations.py --csv registrations.csv --write
```

The script can also consume a Google Sheet URL when its CSV export is accessible:

```bash
python scripts/import_google_registrations.py --sheet-url "<Google Sheet URL>"
```

It defaults to dry-run. Student data is not made public by this code. A private Sheet should be exported/downloaded and passed as CSV unless a future authenticated Google Sheets connector is added.

This is intentional for the MVP: **collect registrations cheaply in Google Sheets, manually approve/enroll, then write only enrolled students to Aiven.**


## Direct Google Form/Sheet webhook

The production registration bridge is also available at:

`POST /api/registrations/google-form`

The endpoint requires the `X-Improvia-Webhook-Secret` header and the same value in Render's `GOOGLE_REGISTRATION_WEBHOOK_SECRET` environment variable. It only writes a student when the submitted row has an approved enrollment status (`APPROVED`, `ENROLLED`, or `ACTIVE`). Blank or other statuses are acknowledged without writing to Aiven.

For the current MVP, the Google Form-bound Apps Script watches the linked response Sheet's `Enrollment Status` column. This keeps the approval gate explicit: a normal form submission does not enroll a student automatically.
