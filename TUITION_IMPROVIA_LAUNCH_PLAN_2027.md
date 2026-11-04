# Tuition Website + Improvia: February 2027 Launch Plan

Status: Planning proposal (26 October 2026). Not an implemented feature specification or validated commercial forecast.

## 1. Business structure and positioning

Maintain separate brands: (1) a personal offline mathematics tuition website serving Behala, Kolkata; and (2) Improvia, an independently accessible assessment and improvement platform. Link the brands through a student portal and secure APIs, not duplicated assessment logic. Improvia should support independent users, not only enrolled tuition students. Keep the core Improvia promise: diagnose where marks are lost, explain why, recommend practice, and track progress.

Existing repository documents `PRODUCT_STRATEGY.md` and `PRODUCT_SCOPE_AND_PILOT_WORKFLOW.md` remain authoritative for Improvia's broader curriculum scope and pilot principles. The tuition launch prioritizes Classes 9–10; it does not remove the existing broader Improvia scope.

## 2. Offline tuition operating model

- Location: Behala, Kolkata; exact venue and eligibility for a Google Business Profile to be confirmed.
- Availability: Saturday and Sunday mornings through early afternoon; three 90-minute slots each day, with short breaks.
- Three recurring batches maximum, each attending **both Saturday and Sunday**. Thus six weekly sessions, **not six separate batches**.
- Target 10 students per batch, maximum planned capacity 30 students. Prioritize Class 10 and Class 9; omit Classes 6–8 if necessary. Batch C may be another Class 9/10 group or board-specific batch according to demand. Do not mix incompatible syllabi indiscriminately.
- Proposed fees: ₹700–₹800 per student **per month for both weekly sessions combined**; final fees and any board-based differentiation to be confirmed.
- Gross monthly revenue at 10/20/30 students: ₹7,000–₹8,000 / ₹14,000–₹16,000 / ₹21,000–₹24,000. This excludes venue, utilities, worksheets, ads, discounts, nonpayment, holidays and founder time. Full-capacity 12-month annualization is not a forecast.
- At full capacity, about 9 contact hours per weekend, excluding preparation, marking, parent communication and software administration.

## 3. Tuition website MVP

Public pages: home, tutor profile, Classes 9–10 course details, timetable/fees, locality, free worksheets, WhatsApp enquiry, privacy/contact information. Mobile-first and accessible from business profile and local search. Avoid publishing exact home address unnecessarily.

Student area: login, own batch, assigned assessments, own results and progress, downloadable worksheets, own fee status/receipts. Teacher area: enrolments/batches, fee ledger, assign tests, view aggregate weak topics and student progress. Keep the student's main navigation to `My Tests`, `My Progress`, `Extra Practice`; payments can appear in a separate account area. Parents should only access their own child's permitted information.

## 4. Integration architecture

- Frontend: React + TypeScript, static hosting such as Cloudflare Pages where terms permit.
- Backend: Python/FastAPI for authenticated APIs and business rules.
- Storage: PostgreSQL; reuse existing Improvia question-bank, taxonomy, scoring, diagnostic and report workflows as source of truth.
- Shared student identity or securely linked identities, with explicit student-to-Improvia mapping; role-based authorization and tenant/record ownership checks on every endpoint.
- Tuition service manages batches, enrolment, fees and referrals. Improvia manages assessments, attempts, evaluation, diagnostics, reports and later optional credits.
- Suggested API boundaries: assign assessment, list assigned assessments, submit attempt, get own result, get authorized report, retrieve progress. Server-to-server credentials must never be exposed to browser code.
- Build an end-to-end tested registration → test → submission → evaluation → report workflow before advanced functionality.
- Child/student privacy: data minimization, age-appropriate consent/parental authorization as applicable, clear privacy notice, retention/deletion processes, secure authentication, backups and access logging. Validate legal obligations before public launch.

## 5. Fees, referrals and optional credits

### Fee management for February MVP

Track monthly invoices/dues, ₹700–₹800 base fee, adjustments, payment status, receipt records and monthly totals. Accept externally collected UPI/bank/cash payments with manual reconciliation; do not treat screenshots as verified payment. Start with manually triggered WhatsApp reminders. Payment gateway and automatic reconciliation are post-MVP options.

### Tuition referral proposal

Give the referring student and newly enrolled student ₹100 off one month each, only after the new enrolment is paid. Cap at two successful rewards per referrer during the initial campaign; record referral attribution and avoid indefinite stacking. Revisit economics after measuring actual acquisition and retention. Do not condition genuine reviews on rewards.

### Improvia credits (defer full rewards to post-launch)

Credits are noncash, nontransferable promotional usage points, separate from rupee tuition-fee discounts. They can unlock optional extra chapter tests, practice packs or mock exams; assigned tests and essential feedback remain available without credits. Proposed illustrative redemption prices: extra chapter test 30, practice pack 20, mock 60. Welcome or tuition credits may be automatic, but detailed reward rules, caps, expiry and anti-abuse protections require validation. Maintain a server-side immutable-style transaction ledger and atomic balance updates. Do not launch paid credit purchase or elaborate gamification in February.

## 6. Improvia commercial model and validation

The 30 tuition students are a controlled real-world pilot, not the ceiling of Improvia's market. Independent students must be able to register and complete an initial diagnostic without tuition enrolment. Test a free entry assessment and a hypothetical ₹49 paid additional assessment/report; do not treat ₹49, subscriptions or conversion rates as validated. Long-term options include tutor/school partnerships after quality and repeat usage are demonstrated. Manual marking may validate the product but cannot scale indefinitely.

Track: qualified enquiries, demo attendance, tuition enrolments, paid retention, ad/referral cost per enrolment, assessment starts/completions, report views, repeat assessments, usefulness feedback, manual marking minutes, cost per report, independent paid conversion and support workload. Do not assume thousands of users or profitable acquisition.

## 7. Marketing and acquisition

Prioritize local referrals, demos, parent word-of-mouth, and an eligible Google Business Profile before paid ads. Public landing page must state area, boards, class levels, schedule, fee, batch size and WhatsApp contact. Target high-intent Behala maths-tuition searches, use relevant negative keywords, and cap the initial Google Search Ads experiment at ₹2,000–₹3,000. Track paid enrolments, not clicks alone. Pause if acquisition costs are unsustainable relative to tuition fees and retention. Avoid major Improvia ad spending before independent-user engagement and willingness to pay are validated.

## 8. Delivery milestones (target public launch: February 2027)

| Period | Focus | Exit gate |
|---|---|---|
| Oct 26–31, 2026 | Audit repository branches, tests, database/migrations and existing flows | Documented baseline and blockers |
| Nov 2026 | Stabilize question bank/taxonomy, assessment, evaluation and PDF reporting | Verified assessment-to-report workflow |
| Dec 2026 | Build public tuition site, worksheets, enquiries, student identity and basic API integration | Public pages work; secure portal prototype |
| Jan 2027 | Fee ledger, pilot with real students, mobile/security testing, backups, ad preparation | Controlled pilot and launch checklist pass |
| Feb 2027 | Launch tuition website + usable Improvia MVP; enrolment/referrals and capped local search ads | Real users complete core workflow |

This schedule is ambitious for a solo part-time founder. If delayed, launch the public tuition site first and gate student accounts/Improvia on security and assessment accuracy. Defer advanced dashboards, AI grading, subscriptions, payments, sophisticated rewards and broad subject expansion.

## 9. Costs and decision gates

Lean initial cash target: approximately ₹700–₹2,000 for domain/basic site plus optional ₹2,000–₹3,000 capped ads and ₹0–₹1,000 marketing materials. This excludes founder time and possible paid production backend, database, email, backups and transaction fees. Earlier production infrastructure planning allowance was roughly ₹600–₹4,000/month depending on service requirements; verify actual vendor prices, commercial hosting terms and renewals before commitment.

Proceed to paid infrastructure when pilot reliability, uptime, security and backup requirements justify it. Scale Improvia acquisition only when reports are accurate, repeat usage is observed and acquisition economics are measured.

## 10. Open decisions

Confirm tuition brand/domain, exact venue, boards per batch, class times, student/parent identity flow, fee due dates, payment methods, referral policy, initial credit policy, whether Improvia's existing API is assessment-ready, hosting and database deployment, and acceptance tests for February launch.
