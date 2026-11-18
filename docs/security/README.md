# Security and student privacy

Students may be minors. Names, contact details, handwritten answers, uploads, submissions, marks, reports and histories are private student data.

## Required verification areas

- Authentication and role/ownership checks on every student-data route.
- Cross-student denial for attempts, uploads, responses, results and reports.
- Private and durable handwritten-answer storage; no public upload paths.
- CSRF protection for state-changing requests.
- Server-authoritative deadlines and valid attempt-state transitions.
- Idempotent submission and protection against post-submission edits.
- Upload type, size and content validation.
- Secure secrets and production configuration with no insecure defaults.
- Backups, restore testing, retention/deletion and incident handling.
- Consent and provider-term review before any third-party processing of student data.

## Evidence

Use [Platform verification](../engineering/PLATFORM_VERIFICATION.md) and the [development audit](../engineering/DEVELOPMENT_AUDIT.md) to distinguish implemented foundations from unverified controls. The [student-access/private-media runbook](../deployment/IMPROVIA_STUDENT_ACCESS_AND_PRIVATE_MEDIA_RUNBOOK.md) is a prepared procedure, not authorisation to perform production changes.

Never send real student work or personal information to an AI/external provider without explicit approval and appropriate consent/privacy review. Do not use unsupervised AI grading.
