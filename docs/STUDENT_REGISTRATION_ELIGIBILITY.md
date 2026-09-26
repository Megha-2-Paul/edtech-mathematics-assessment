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

## Google Forms integration boundary

There is still no live Google Forms → Sheets → Aiven connector in the repository. The form can continue to be collected in Google Sheets first. A future controlled enrollment step can construct a `Student` using the fields above and call `register_student()`.

This implementation deliberately does not invent or add an automatic public registration endpoint.
