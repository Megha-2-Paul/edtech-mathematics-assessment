# Improvia Commercial Platform Roadmap
## Security, product validation, operational readiness and responsible scale

**Project:** Improvia — Mathematics Assessment & Improvement System  
**Repository:** `Megha-2-Paul/edtech-mathematics-assessment`  
**Document status:** Strategic requirements and staged acceptance criteria; not evidence that any item is implemented or production-ready.  
**Planning horizon:** Controlled launch target: February 2027, subject to release gates.  
**Primary market:** India; CBSE / ICSE Mathematics, initially Classes 10–12.  
**Current documented stack:** Python, Flask, Jinja2, SQLAlchemy, MySQL; Render application hosting; Aiven MySQL production database; Cloudinary currently documented for image storage. Verify actual live configuration before relying on it.

---

## 1. Executive direction

Improvia must operate as a trustworthy education product, not merely a test-taking website. Its core promise is:

> Show students where they lose marks, why they lose them, what to practise next, and whether they improve.

The product loop is:

**Register → Confirm eligibility → Assess → Save answers → Submit → Evaluate → Diagnose → Report → Recommend practice → Reassess → Measure improvement.**

Commercial readiness depends on proving this loop safely and accurately with real users. More features, AI, integrations, dashboards or tenant types do not compensate for incorrect marks, exposed student data, unreliable submissions or reports that do not help learners.

### Product boundaries

- Keep Improvia focused on mathematics assessment, human-confirmed evaluation, explainable diagnosis and improvement measurement.
- Keep the existing Flask / SQLAlchemy / MySQL architecture unless a separately approved technical decision demonstrates that a migration is necessary.
- Keep local development MySQL separate from production Aiven MySQL. Do not introduce general-purpose two-way replication.
- Keep tuition-centre administration and assessment records logically separate. Fee/payment records must never affect marks, diagnosis or assessment eligibility calculations except through an explicit, audited access-entitlement rule.
- Institutional / multi-tenant SaaS and company-specific deployments are possible later directions, not permission to expand the current launch scope.
- Do not introduce a general-purpose business analytics product, ERP, marketplace or unrelated workflow platform under the Improvia name.

## 2. Product and customer model

### 2.1 Initial customer groups

1. **Individual students and guardians:** purchase or receive access to a diagnostic assessment and useful feedback.
2. **Founder-operated tuition cohort:** a small supervised group used to test the assessment, marking, reporting and improvement loop.
3. **Tutors / coaching centres:** a later institutional customer group, only after the individual workflow is reliable and educator demand is demonstrated.
4. **Schools / larger organisations:** a later stage requiring validated permissions, tenant isolation, support, service commitments and operational capacity.

The tuition cohort is an early validation channel, not the entire addressable market. Independent Improvia users must remain possible without enrolling in local tuition.

### 2.2 Commercial hypotheses, not facts

- A free first diagnostic can reduce adoption friction.
- ₹49 for an additional assessment/report has been discussed as a pricing hypothesis; it is not validated or approved as a permanent price.
- Registrations, enquiries and free-test completions do not prove willingness to pay.
- Revenue examples are arithmetic scenarios, not forecasts.
- Human marking time, support effort, hosting, storage, messaging, payment fees, refunds, tax and customer acquisition costs must be measured before claiming profitability.

### 2.3 Customer discovery and validation

Before expanding the product:

- Interview students and guardians about how they currently identify and correct mathematics mistakes.
- Interview tutors / centre owners about marking effort, report usefulness, workflow fit and willingness to pay.
- Ask users to explain the report back in their own words; do not rely only on satisfaction scores.
- Observe whether students complete the recommended practice and return for another assessment.
- Record objections, support requests, marking time and reasons for non-completion.
- Obtain permission before using student work, quotes, testimonials or results in marketing.
- Do not promise score improvements, board outcomes or guaranteed results.

## 3. Current architecture and source-of-truth policy

The current repository documentation describes the following production topology. It must be re-verified against live provider settings before release:

```text
Student / Guardian Browser
          |
          v
Flask application (documented on Render)
          |
          +---- Aiven MySQL (documented production source of truth)
          |       Students, tests, questions, attempts,
          |       responses, evaluations and history
          |
          +---- Private answer / report storage
          |       (storage privacy and durability must be verified)
          |
          +---- Controlled integrations
                  Email / WhatsApp / workflow orchestration
```

### 3.1 Architecture rules

- Aiven MySQL remains the production source of truth for student and assessment records unless a separately approved architecture decision replaces it.
- Local MySQL is for development and testing, not a second live source of truth.
- Google Sheets may hold raw registration and validation responses during the controlled launch. It must not silently become a second synchronized production database.
- Registration-to-database processing must be reviewed, retryable and idempotent.
- The optional question-bank sync is not general database replication.
- The browser must never connect directly to the production database.
- Secrets and provider credentials must remain server-side and outside the repository.
- Workflow tools such as n8n may orchestrate notifications and jobs; core authentication, timer authority, marks, analytics and diagnosis remain in the application/domain layer.
- Do not migrate to FastAPI, React, PostgreSQL, a new queue or another hosting provider merely because those technologies are available. Any stack migration needs a separate cost, risk, compatibility and rollback plan.

### 3.2 Future institutional architecture

If institutional customers are validated, design an explicit organisation / tenant model before offering shared multi-tenant access. A future tenant model may include organisations, memberships, roles, student enrolments, assessments, reports, billing entitlements and audit events.

Do not retrofit tenant identity casually into existing student or assessment tables. Before multi-tenant launch:

- Define tenant ownership for every relevant record and file.
- Enforce tenant scope in every query, background job, report, export and storage operation.
- Add database constraints and indexes that support tenant-scoped access.
- Test cross-tenant access denial for every role and object type.
- Define tenant onboarding, offboarding, data export, deletion, retention and support boundaries.
- Decide whether shared SaaS, isolated databases or customer-specific deployments are commercially and operationally justified.
- Document the threat model and test tenant isolation before accepting customer data.

Institution-specific deployments may be considered later, but must not create a second unsupported product architecture or undermine the single source of truth.

## 4. Security and privacy baseline — release blockers

Security is a release condition, not a later enhancement. The requirements below are targets to verify in code, configuration and tests; this document does not assert that they are already satisfied.

### 4.1 Identity, authentication and sessions

- Every student accessing attempts, submissions, answer images, results or reports must have an authenticated, active account.
- Never create anonymous guest identities for real student use.
- Use established password hashing; never store plaintext passwords or reversible password values.
- Activation and recovery tokens must be random, hashed at rest, short-lived, single-use and invalidated when superseded.
- Apply rate limits and safe lockout / recovery behaviour to authentication endpoints.
- Clear or rotate sessions on login, logout and privilege changes; use secure cookie settings and appropriate expiry.
- Require stronger authentication for staff / teacher / administrator accounts where practical, with MFA considered a launch requirement for privileged production access.
- Do not reveal whether an email, phone number or student ID exists through login and recovery error messages.
- Define a safe process for guardian-assisted account recovery for minors.

### 4.2 Authorisation and ownership

- Apply least privilege and deny access by default.
- Check ownership and role permissions on every route, API, download, export, background task and object-storage operation that touches student data.
- A student may access only their own attempts, responses, answer images, reports and progress history.
- A teacher may access only students and assessments they are authorised to manage.
- Administrative access must be limited, attributable and auditable.
- Never rely on hidden buttons, frontend checks or unguessable IDs as authorisation.
- Test anonymous, owner, other-student, authorised-teacher and unauthorised-teacher cases.
- If multi-tenancy is introduced, add cross-tenant denial tests in addition to student-level ownership tests.

### 4.3 CSRF, web security and abuse prevention

- Protect every state-changing browser form and applicable POST / PUT / PATCH / DELETE route with CSRF controls.
- Use HTTPS for all production traffic; redirect or reject insecure requests as appropriate.
- Configure secure, HttpOnly and SameSite session cookies according to the authentication flow.
- Validate redirects, origins, content types and request methods.
- Apply rate limits to login, activation, upload, submission, report generation and public registration endpoints.
- Set request body, upload and processing limits to reduce denial-of-service risk.
- Use secure response headers and a restrictive Content Security Policy where compatible with the application.
- Prevent SQL injection, cross-site scripting, path traversal, insecure direct object references and unsafe deserialisation.
- Keep dependencies patched; review security advisories and remove unused dependencies through a separate approved change.

### 4.4 Secrets and configuration

- No secrets, passwords, database URLs, API keys, tokens, webhook signing keys or private student data may enter Git, issue comments, logs, screenshots or public documentation.
- Production must not use development fallback secrets or default credentials.
- Fail safely when required production configuration is missing or invalid.
- Use environment-based secret management and restrict who can read or rotate production secrets.
- Rotate any credential suspected of exposure and review relevant access logs.
- Keep development, CI, staging and production credentials separate.
- Never paste real secrets into chat or commit them to a sample configuration file.

### 4.5 Private handwritten work, reports and uploaded files

Handwritten mathematics answers and generated reports are sensitive student records.

- Store answer images and private reports in durable private storage; public bucket or public delivery URLs are not acceptable.
- Remove or prevent direct public access to raw upload paths.
- Use short-lived signed URLs or an authenticated proxy after verifying object ownership and requester permissions.
- Verify the actual privacy mode of Cloudinary or any replacement provider. Legacy public assets need a separate inventory and remediation plan.
- Validate file extension, detected MIME type, file signature, size, dimensions and allowed formats; do not trust the browser filename or content-type header.
- Use random server-generated storage keys; never use user-controlled paths.
- Defend against path traversal, oversized decompression, malformed images and resource-exhaustion attacks.
- Consider malware scanning and safe image re-encoding before making uploads available to staff.
- Apply retention and deletion rules to originals, thumbnails, temporary files and generated reports.
- Test upload failure, missing file, invalid type, oversized file, duplicate upload, replacement, deletion, anonymous access and cross-student access.
- Do not expose student names, phone numbers, IDs or private storage URLs in public URLs or logs.

### 4.6 Logging, audit and incident response

- Log security-relevant events: authentication failures, access denials, account changes, upload access, submission, evaluation edits, report delivery and administrative actions.
- Do not log passwords, tokens, full answer content, private image URLs or unnecessary personal data.
- Record who changed marks, error codes, comments or evaluation status, when, and what changed.
- Restrict log access and define retention.
- Prepare an incident response procedure covering triage, containment, credential rotation, evidence preservation, affected-user communication and legally required notifications.
- Define a contact and escalation path for students / guardians reporting account or privacy issues.

## 5. Student privacy and legal readiness

Students may be minors. Privacy design and guardian communication must be completed before real student data is processed.

This section is a compliance checklist, not legal advice or a determination that a particular law or provision applies to every workflow. Obtain qualified India-specific legal advice and verify current commencement dates, rules and regulator guidance before launch.

### 5.1 Privacy programme

- Publish a clear privacy notice in language students and guardians can understand.
- Explain what data is collected, why it is needed, how it is used, who can access it, which providers process it, how long it is retained and how users can request help.
- Collect only information necessary for registration, assessment delivery, evaluation, reporting, safety and support.
- Separate optional marketing consent from essential assessment processing.
- Record consent version, timestamp, purpose, guardian relationship and withdrawal where applicable.
- Establish a guardian consent / verification process where required for children.
- Define age handling and avoid behavioural advertising or unnecessary profiling of minors.
- Provide a process for access, correction, withdrawal, deletion and grievance requests where applicable.
- Set retention periods for registrations, answer images, reports, logs, backups and inactive accounts.
- Document deletion from primary systems, storage providers and eventual backup expiry.
- Maintain a processor / vendor register, data-processing terms and a review of data location, subprocessors, retention, training use and breach notification.
- Do not use student data to train models or for unrelated purposes without a lawful basis, appropriate consent and explicit owner approval.

### 5.2 India-specific legal review

Before onboarding real students, review applicability and obligations under the Digital Personal Data Protection Act, 2023, the notified DPDP Rules and their commencement / transition provisions, the Information Technology Act and applicable rules, consumer-protection and e-commerce requirements where relevant, payment-provider requirements, and tax / invoicing obligations.

The review must specifically cover:

- Children’s personal data and verifiable parental consent where required.
- Notice, purpose limitation, data minimisation and retention.
- Data principal requests and grievance handling.
- Processor contracts and third-party service terms.
- Security safeguards and personal-data breach response / notification.
- Cross-border transfers and provider data locations.
- Marketing claims, refund terms, pricing display and consumer complaints.
- GST, accounting and invoice obligations with a qualified accountant.

Do not treat a generic website privacy-policy template as proof of compliance.

## 6. Assessment integrity and educational quality

### 6.1 Server-authoritative exam lifecycle

- The server is authoritative for start time, deadline, remaining time, attempt state and submission status.
- Persist start time and a server-computed deadline.
- Enforce expiry on the server, not only with a browser countdown.
- Saving answers and uploads must be ownership-checked and constrained to an active attempt.
- Refresh / reconnect must resume the same attempt and remaining server-calculated time.
- Submission must be atomic and idempotent; repeated clicks or retries must not create duplicate results.
- Submitted attempts must be immutable except through a separately authorised, audited correction workflow.
- Define and test valid state transitions, expiry behaviour, interrupted uploads and partial failures.
- Materialise unanswered responses consistently so evaluation completeness can be checked.
- Provide a submission receipt and clear student-facing status.

### 6.2 Marking policy

- Objective responses may be automatically checked against approved answer keys.
- Handwritten / subjective answers must be marked by a human in the initial commercial release.
- No unsupervised AI grading.
- Future AI may suggest transcription, marks, error codes or explanations only after explicit approval, privacy / consent review and benchmark validation. A human must confirm every subjective mark.
- Preserve the existing error taxonomy unless a code review justifies a change:

| Code | Meaning |
|---|---|
| C01 | Calculation |
| C02 | Conceptual |
| C03 | Formula |
| C04 | Sign |
| C05 | Incomplete steps |
| C06 | Wrong method |
| C07 | Missing justification |
| C08 | Misunderstood question |
| C09 | Time / attempt issue |

- A blank or unanswered question alone is not proof of a conceptual weakness.
- Support partial marks and multiple applicable error codes where the rubric allows.
- Keep marking comments specific, constructive and understandable.
- Define recheck / correction and replacement-photo processes.
- Audit every mark and evaluation change.

### 6.3 Report and diagnosis validation

- Use deterministic, explainable scoring and diagnosis rules for the initial release.
- Validate all report totals, percentages, attempt rates, accuracy, chapter scores, error counts and marks-lost figures against hand-calculated examples.
- Use fixed golden datasets with expected results.
- Test partial marks, unanswered questions, multiple error codes, missing evaluations, repeat attempts and incomplete submissions.
- Version scoring and diagnosis rules so historical reports remain interpretable.
- Distinguish measured evidence from inferred weakness; show uncertainty when evidence is sparse.
- Recommendations must map to actual observed errors and available practice material.
- Reports should explain where marks were lost, why, what to practise next and what changed since the previous assessment.
- Do not claim improvement unless assessments are reasonably comparable and the evidence supports the comparison.
- Ensure reports are private, accessible only to the student and authorised staff / guardians as configured.

## 7. Database integrity, migrations and recovery

### 7.1 Data integrity

- Maintain stable student, question, test and attempt identifiers.
- Enforce appropriate foreign keys, uniqueness constraints, status constraints and indexes.
- Keep board, class and subject identity explicit in curriculum relationships.
- Use transactions for related state changes, especially submission, evaluation completion and payment reconciliation.
- Make registration, webhook processing, submission, payment recording and notification retries idempotent.
- Separate financial records from learning / assessment records.
- Prevent duplicate student identities through an explicit, reviewed matching rule; do not merge accounts based only on a weak name match.
- Define data correction procedures with audit history rather than silent overwrites.
- Validate marks, maximum marks, numeric ranges and ownership on the server.

### 7.2 Migration discipline

- Inspect the actual migration history before selecting a migration number.
- Never edit a migration that may already have run; add a new correctly ordered migration.
- Review migration dependencies, idempotency, locks, data backfills, runtime and rollback.
- Run migrations first against disposable local / CI MySQL, then a reviewed staging copy where available.
- Take and verify a production backup before any approved production migration.
- Never run production Aiven migrations or destructive writes from this workflow.
- Do not assume that a migration file or documentation proves the live schema is current.
- Preserve existing migration and PR work; reconcile conflicting migration branches deliberately rather than merging overlapping changes blindly.

### 7.3 Backup and disaster recovery

- Define recovery point objective (RPO) and recovery time objective (RTO) based on actual student and business needs.
- Confirm database backup frequency, retention, encryption, access controls and provider responsibilities.
- Back up private answer images and reports as well as database metadata; a database-only backup is incomplete.
- Keep backups protected from the same credentials and failure modes as production.
- Perform restore drills into an isolated environment and record exact duration and data-loss window.
- Verify referential integrity and file-to-database consistency after restore.
- Document who can authorise restore, failover and recovery.
- Do not claim disaster recovery readiness until a restore has been successfully demonstrated.

## 8. Payments, fees and commercial controls

### 8.1 Separate assessment payments from tuition fees

- Keep Improvia assessment purchases / entitlements separate from local tuition fee management.
- Do not store card details or sensitive payment credentials.
- Use a reputable payment provider only after fees, settlement, refund, dispute, webhook and data-processing terms are reviewed.
- Verify payment status server-side using authenticated provider callbacks / API verification; a screenshot or user-entered transaction ID is not proof of payment.
- Verify webhook signatures, timestamps and replay protection.
- Make payment-event processing idempotent.
- Record order, amount, currency, provider reference, status, timestamps, refunds and reconciliation evidence.
- Do not grant paid access solely because the browser returns to a success page.
- Define cancellation, refund, failed-payment, duplicate-payment and chargeback handling.
- Keep invoices / receipts and accounting records separate from assessment marks.

### 8.2 Pricing and unit economics

- Validate willingness to pay through actual transactions, not survey intent alone.
- Calculate contribution margin after payment fees, hosting, storage, messaging, marking time, support, refunds, tax and acquisition cost.
- Track founder marking time per paper and per question.
- Track support minutes per student and cost per completed report.
- Review whether a low assessment price can sustainably cover human marking and support.
- Do not launch subscriptions or stored-value credits until recurring value, refund rules, ledger integrity and customer demand are demonstrated.
- Keep pricing, taxes, refund terms and service limitations visible before purchase.

## 9. Integrations and third-party services

Every external integration expands the security and operational boundary.

- Maintain an inventory of integrations, purpose, data shared, credentials, owner and provider terms.
- Send the minimum data needed for the task.
- Never send student names, contact details, handwritten answers or reports to an AI / external provider without explicit approval, appropriate consent and a provider privacy / retention review.
- Use separate credentials per environment and least-privilege scopes.
- Authenticate webhooks with signatures or equivalent shared-secret verification; reject stale or replayed events.
- Make webhook handlers idempotent and retry-safe.
- Apply timeouts, bounded retries, dead-letter / failure visibility and manual replay controls.
- Avoid logging request bodies containing student data or secrets.
- Document provider outages and manual fallback procedures.
- Confirm commercial-use rights and licensing for question sources, worksheets, fonts, images and generated content.
- AI extraction remains experimental until benchmarked against human-verified references; preserve source/page provenance and require human review before publication.

## 10. Operational and deployment readiness

### 10.1 Environments and releases

- Keep local, CI, staging and production isolated.
- Use synthetic data in development and CI; never copy real student data into test environments without explicit authorisation and safeguards.
- CI must run the relevant exam-platform tests and disposable MySQL integration tests.
- Include security, access-control, upload, timer, duplicate-submission, evaluation and report regression tests.
- Review migrations separately from application deployment.
- Know whether the hosting provider will auto-deploy when a branch changes or a merge occurs.
- Deploy a reviewed, tested commit; retain the previous known-good release and documented rollback procedure.
- Verify health checks, database connectivity, storage access, email / webhook configuration and student login after deployment.
- Do not equate CI success with production readiness.

### 10.2 Monitoring and support

- Monitor application errors, latency, database availability, storage failures, queue / webhook failures, upload failures and report-generation failures.
- Alert on repeated authentication failures, access-control anomalies and unusual data access.
- Use correlation IDs that do not expose student identity.
- Establish a support contact, response expectations, issue triage and escalation process.
- Prepare student-facing service notices for planned maintenance and outages.
- Record incidents and corrective actions.
- Review operational cost and capacity monthly during the pilot.

### 10.3 Reliability and performance

- Avoid N+1 database access and unbounded list / report queries.
- Paginate growing student, test and evaluation lists.
- Process large files and report jobs without loading all content into memory.
- Move slow report generation, image processing and notifications to bounded background work when justified.
- Add timeouts and failure handling to provider calls.
- Test on low-bandwidth mobile connections and small screens.
- Define availability and support targets only when the service can measure and meet them.

## 11. Commercial validation and pilot design

### Phase 0 — Security, integrity and release readiness

**No real-student public launch until all critical gates pass.**

- Reconcile existing security work and PR dependencies against current `master`; do not assume open PRs are merged.
- Verify authenticated student access and teacher permissions on every sensitive route.
- Verify durable private answer-image storage and private report delivery.
- Resolve legacy public image exposure or document an approved, safe remediation before using affected assets.
- Verify server-side deadlines, attempt-state transitions and idempotent submission.
- Review CSRF across state-changing routes, upload validation, secrets and production configuration.
- Inspect migration history and audit migrations read-only first.
- Demonstrate backup and restore for database and files.
- Verify the core workflow with synthetic data and hand-checked reports.

### Phase 1 — Founder-operated assessment loop

Prove one complete assessment cycle before adding automation:

1. Registration received and reviewed.
2. Eligibility confirmed.
3. Permanent student identity created or reused.
4. Assessment assigned and access granted.
5. Student starts, answers, refreshes / resumes and uploads handwritten work.
6. Student submits once and receives confirmation.
7. Objective responses are checked; subjective responses are manually marked.
8. Marks, comments and C01–C09 codes are reviewed and saved with an audit trail.
9. Diagnosis and report are generated and checked.
10. Report is securely delivered.
11. Student profile is updated.
12. Next practice focus is explained.
13. A second assessment measures change.

Measure marking time, support effort, upload failure rate, completion, report corrections and student understanding.

### Phase 2 — Closed supervised pilot

- Start with approximately 5–10 supervised students using synthetic test accounts for technical rehearsals and real data only after privacy / security gates pass.
- Keep founder-led manual marking and review.
- Obtain guardian consent where required.
- Collect structured student / guardian feedback and record actual behaviour.
- Hand-check a sample of every report calculation.
- Track completion, time to report, usefulness, practice follow-through, reassessment and support effort.
- Pause if access, privacy, marking accuracy or data integrity issues arise.
- Do not scale based only on registrations or positive comments.

### Phase 3 — Small paid launch

Move toward 20–30 paying students only when the closed pilot demonstrates reliable delivery and genuine value.

Acceptance evidence should include:

- No unresolved critical security or privacy findings.
- Successful database and file restore drill.
- Verified registration-to-report workflow.
- Correct reports against golden examples.
- Human-confirmed subjective marks and auditable corrections.
- Measured marking capacity and support workload.
- Transparent pricing, refund and privacy terms.
- Evidence of repeat assessment interest and actual willingness to pay.
- A sustainable, measured cost per acquired paying student.

### Phase 4 — Institutional validation and SaaS readiness

Only after the individual product works:

- Interview and pilot with one or a small number of educators / centres.
- Validate their workflows separately; do not assume school, tuition-centre and individual student permissions are identical.
- Test organisation onboarding, role administration, roster import, assignments, reports, exports and support.
- Build and test tenant isolation before storing data from multiple organisations in shared infrastructure.
- Validate subscription / contract willingness, onboarding cost, support burden and renewal intent.
- Offer dedicated deployments only when customer demand and operational capacity justify them.

## 12. Metrics and evidence dashboard

Define metric formulas before collecting results. Segment by acquisition source, board/class, assessment type and cohort where sample sizes protect privacy.

| Area | Measures |
|---|---|
| Acquisition | Qualified enquiries, registration completion, source, cost per qualified enquiry |
| Activation | Eligible students, first assessment start, start-to-completion rate |
| Reliability | Upload success, autosave / resume success, duplicate submission incidents, service errors |
| Evaluation | Time to mark, time to report, correction / recheck rate, pending evaluation age |
| Learning value | Marks lost by error type, report comprehension, practice follow-through, comparable reassessment change |
| Retention | Second assessment rate, time to reassessment, repeat purchase / participation |
| Commercial | Paid conversion, realised revenue, refunds, payment failures, contribution margin |
| Operations | Support minutes per student, incidents, restore duration, provider / storage cost |
| Institutional | Educator activation, roster success, staff adoption, renewal intent, support cost per organisation |

Do not set arbitrary success percentages before a baseline exists. Agree pilot thresholds in advance, document why they matter and report both positive and negative evidence.

## 13. Explicitly deferred until evidence supports them

These are not prerequisites for the first safe commercial assessment loop:

- Autonomous AI marking or grading.
- Automatic finalisation of handwritten marks.
- Full handwriting OCR / vision-based evaluation.
- Adaptive test generation.
- Complex credits, wallet or gamification systems.
- Large parent / school / tutor dashboard suites.
- Mobile native applications.
- Broad subject / board expansion.
- Marketplace functionality.
- Subscription billing before repeat value is demonstrated.
- Multi-tenant SaaS before tenant isolation and institutional demand are validated.
- Customer-specific deployments before support and release processes exist.
- Framework or database migration without a separate approved business and technical case.

Deferred does not mean rejected permanently; each item requires its own evidence, threat model, cost assessment and approval.

## 14. Release acceptance checklist

A release owner should record evidence and a named reviewer for each gate.

### Security and privacy
- [ ] Student authentication and account recovery verified.
- [ ] Role and ownership checks verified across all student-data routes and files.
- [ ] CSRF and abuse controls verified for state-changing routes.
- [ ] Production secrets and configuration reviewed; no insecure defaults.
- [ ] Private uploads and reports verified, including legacy asset inventory.
- [ ] Privacy notice, consent / guardian process and retention schedule reviewed.
- [ ] Third-party processors and AI data-sharing permissions reviewed.
- [ ] Incident and grievance procedures documented.

### Assessment and data integrity
- [ ] Server-authoritative timers and deadlines verified.
- [ ] Attempt state transitions and duplicate submission protection verified.
- [ ] Upload and resume failure cases tested.
- [ ] Manual marking and audit trail verified.
- [ ] Golden report calculations pass, including partial marks and unanswered items.
- [ ] Student-to-student and teacher access boundaries tested.
- [ ] Migration history reviewed and schema matches the release.

### Operations
- [ ] CI and relevant MySQL integration tests pass.
- [ ] Production deployment and rollback procedure reviewed.
- [ ] Database and file backups configured.
- [ ] Restore drill completed and timed.
- [ ] Monitoring, alerts and support ownership established.
- [ ] Mobile / low-bandwidth workflow checked.
- [ ] Provider outages and manual fallback documented.

### Commercial
- [ ] Customer problem and report usefulness validated with real users.
- [ ] Pricing and refund terms are visible and reviewed.
- [ ] Payment verification and reconciliation tested if payments are enabled.
- [ ] Marking and support capacity measured.
- [ ] Actual costs and contribution margin calculated.
- [ ] Pilot and scale thresholds agreed before expansion.

A checked box must link to evidence (test output, configuration review, restore record, signed-off policy or pilot result). A checkbox alone is not proof.

## 15. Governance and change control

- Keep the repository's `docs/CHATGPT_INSTRUCTIONS.md` binding.
- Inspect current `master`, tests, CI, migrations and related PRs before implementation.
- Plan first and wait for explicit approval before code or schema changes.
- Do not create branches, merge PRs, push, rewrite history, deploy or run production migrations without specific authorisation.
- Keep each approved change small, reversible and testable.
- Never weaken or skip tests to make a release appear ready.
- Record decisions, owners, evidence, limitations and unresolved risks.
- Separate documented, planned, implemented, tested and live functionality in all status reports.
- Revisit this roadmap after pilot evidence; do not turn every future idea into an immediate requirement.

## 16. Related repository documents

Use these documents together; this roadmap does not replace their detailed implementation guidance:

- `docs/CHATGPT_INSTRUCTIONS.md` — mandatory repository workflow, security and testing rules.
- `PRODUCT_WORKFLOW.md` — canonical assessment, evaluation, diagnosis and reporting workflow.
- `PRODUCTION_ARCHITECTURE.md` — documented Render / Aiven topology and controlled registration approach.
- `docs/IMPROVIA_REVIEW_AND_IMPROVEMENT_BACKLOG_V2.md` — risks, release blockers and staged assessment backlog.
- `docs/STUDENT_REGISTRATION_ELIGIBILITY.md` — registration and eligibility design.
- `docs/TEACHER_EVALUATION_CUSTOMER_VALUE_DESIGN_PLAN.md` — human evaluation and student value design.

### Status statement

This document defines a target operating standard and evidence-based roadmap. It does not certify that the application, hosting, database, storage, legal compliance, security controls, payment flows, backups, recovery or business model currently meet that standard. Each claim must be verified against current code, live configuration, tests and operational evidence before launch.
