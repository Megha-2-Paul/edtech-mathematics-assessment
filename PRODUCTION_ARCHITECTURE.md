# Production Architecture and Registration Plan

## Verified production topology

As of the current deployment audit, the Render service uses:

- `DATABASE_URL` — configured and points to Aiven MySQL.
- `CLOUDINARY_URL` — configured for hosted object/image storage.
- `SECRET_KEY` — configured.
- `TEACHER_ACCESS_USERNAME` / `TEACHER_ACCESS_PASSWORD` — configured.
- `TESTING_MODE` — configured.
- `QUESTION_BANK_SYNC_DATABASE_URL` — not configured in the inspected Render environment.

Therefore Aiven is currently the **primary production database**, not a secondary student database.

```text
                         PRODUCTION

Student Browser
      ↓
Render / Flask Application
      ↓
DATABASE_URL
      ↓
Aiven MySQL
      ├── Students
      ├── Tests
      ├── Questions
      ├── Attempts
      ├── Responses
      ├── Evaluations
      └── Longitudinal history
```

## Development vs production

Local development and production are separate environments:

```text
LOCAL
Developer machine
  ↓
Local MySQL
  ↓
Development / testing

PRODUCTION
Render
  ↓
Aiven MySQL
  ↓
Real student/application data
```

There is no requirement for continuous local ↔ Aiven synchronization.

A developer can test changes against local MySQL and deploy the application to Render when the changes are ready.

## Question-bank sync clarification

The repository contains `exam_platform/question_sync.py`, which supports an optional primary-to-secondary question-bank sync through:

```text
QUESTION_BANK_SYNC_DATABASE_URL
```

This mechanism is specifically for question-bank data. It should not be treated as a general database replication mechanism.

Because the inspected Render environment does not currently define that variable, the optional secondary question-bank sync is not part of the current production topology.

## Student registration: current prototype vs launch flow

### Current prototype behavior

The current Flask prototype can create a session-based Student_ID and a `Guest Student` record when an exam flow is exercised without an existing student record.

That is useful for prototype testing but should not be the permanent registration mechanism for the controlled launch.

### Controlled-launch target

The registration process should be:

```text
Google Form
      ↓
Google Sheets
      ↓
Registration validation / confirmation
      ↓
Create or reuse permanent Student_ID
      ↓
Aiven MySQL
      ↓
Grant assessment access
      ↓
Student uses Flask assessment site
```

Google Sheets is appropriate for the current registration and customer-validation stage because it allows the founder to review submissions before creating production student records.

The raw Form Responses sheet should remain intact.

## What belongs in Google Sheets

The current registration form collects both operational registration fields and validation/customer-research answers.

Operational fields include:

- Student name
- Email
- WhatsApp/phone
- Class
- Board
- Mathematics / Applied Mathematics
- Registration context

Validation/research fields can include:

- Preparation level
- Frequency of losing marks
- Whether the student understands why marks were lost
- Common mistake types
- Recent score range
- Improvement priorities
- Study/practice behaviour
- Report usefulness expectations
- Future assessment intent
- Acquisition source
- Communication consent

The research answers do not need to be copied into the core `students` table merely because they were collected during registration.

## What belongs in Aiven

Once a student is confirmed for the assessment, the production database should contain the information needed to operate the platform:

- Permanent `Student_ID`
- Name
- Email
- Phone
- Class
- Board
- School where applicable
- Registration date
- Registration source
- Status
- Assessment/test history
- Attempts
- Responses
- Evaluations
- Performance profile/history

The existing student table already has fields for the core registration information. No schema change is currently required for this plan.

## Student identity rule

The important rule is:

> Do not create a new Student_ID every time the same registered student starts an assessment.

The enrollment logic should first attempt to identify an existing student using the registration identity available to the platform. If the student already exists, reuse the permanent Student_ID. If not, create one.

The existing storage layer currently creates/updates by Student_ID and does not itself perform an email/phone identity lookup before creating a student. That lookup should therefore be handled deliberately when the registration/enrollment flow is implemented.

## Failure handling

When registration is eventually automated, treat production enrollment as a small workflow rather than a blind database insert:

```text
Validate registration
      ↓
Create/reuse Student_ID in Aiven
      ↓
Confirm database write
      ↓
Mark registration as enrolled
      ↓
Send assessment access / confirmation
```

If a downstream step fails after the database write, the process should be retryable and idempotent. It should not create duplicate Student_IDs.

## Source-of-truth policy

For the controlled launch:

| Data | Source of truth |
|---|---|
| Raw registration / validation responses | Google Sheets |
| Production student/account record | Aiven MySQL |
| Production assessment data | Aiven MySQL |
| Local development data | Local MySQL |
| Question-bank secondary copy, if enabled later | Optional secondary DB only |

Aiven should remain the production source of truth for the platform.

Google Sheets should not become a second continuously synchronized production database.

## What should NOT be changed yet

Do not introduce:

- Local ↔ Aiven two-way replication
- A second student database
- A new student-table schema solely for Google Forms
- AI grading
- Complex authentication architecture solely for registration
- Automatic Google Sheets → database sync before the registration workflow is validated

The next implementation should be the smallest reliable bridge from a reviewed registration row to an existing `students` record in Aiven.

## Recommended implementation sequence

1. Continue collecting registrations in Google Sheets.
2. Review/confirm the first cohort manually.
3. Define the exact identity matching rule for returning students.
4. Implement a small registration/enrollment service that creates or reuses `Student_ID`.
5. Write the confirmed student to Aiven.
6. Replace the prototype Guest Student path for real assessments.
7. Give only enrolled students access to the assessment.
8. Test the complete flow with a small cohort.
9. Only then automate the Sheet → Aiven step through n8n or another controlled integration.

This keeps the current database schema and application architecture stable while moving from prototype registration to real student enrollment.
