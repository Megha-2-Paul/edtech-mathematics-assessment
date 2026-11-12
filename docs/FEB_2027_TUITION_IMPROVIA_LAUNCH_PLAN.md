# February 2027 Launch Plan — Tuition Website + Improvia
_Status: planning proposal, 26 October 2026. Not a claim of implemented features._

## 1. Strategy and boundaries
Operate two distinct but connected brands:
- **Local mathematics tuition:** founder-led offline weekend batches in Behala, Kolkata; initial focus Classes 9–10, with Classes 6–8 optional depending on demand.
- **Improvia:** independent, scalable assessment and improvement product, accessible to students who do **not** attend tuition. Tuition students form an early validation cohort, not the entire market.
- February 2027 is the **target for a controlled public launch**, not a guarantee of a complete platform.

Core Improvia proposition: **Test → Evaluate → Diagnose errors → Report → Recommend practice → Reassess → Measure improvement**. Preserve subject-specific taxonomy and manual subjective marking until validated alternatives exist.

## 2. Tuition operating model
- Available **Saturday and Sunday**, three 90-minute class slots per day (illustrative: 08:00–09:30, 09:45–11:15, 11:30–13:00).
- **Each batch attends BOTH days** in the same time slot: 3 distinct batches, **10 students each**, 30 students maximum initially; 6 sessions/week, 9 contact hours/week.
- Proposed batches: Class 10, Class 9, and a second Class 9/10 batch based on board-specific demand. Do not mix incompatible syllabuses simply to fill seats.
- Planned fee **₹700–₹800 per student per month**, including both weekly sessions (confirm policy before publishing). Gross full-capacity revenue **₹21,000–₹24,000/month**, excluding costs, holidays, vacancies, discounts and non-payment.
- Fill the first batch before opening more. Validate location, class length, safety, syllabus and actual parent demand.

## 3. Tuition website — distinct brand
Public mobile-first website linked from eligible Google Business Profile:
- Teacher profile, qualifications, teaching approach, locality, class/board pages, timetable, fees, batch capacity, WhatsApp enquiry.
- Free worksheets and demo/diagnostic invitation.
- Separate student login, assigned tests, progress view; simple parent fee view where permissions allow.
- Website and Improvia have separate branding and URLs/domains, with a clear link between them. Buy one domain initially; second domain later if justified.
- Do **not** build a marketplace or a second question bank.

## 4. Integration architecture — align with existing repository
**Current documented reality:** existing Improvia application uses **Flask**, **Render**, **Aiven MySQL** (production source of truth), Cloudinary for images, a controlled Google Forms → Sheets → reviewed enrollment workflow, and a canonical question bank. Do not assume FastAPI/PostgreSQL are already deployed: earlier conversational suggestions were **alternatives**, not verified project state.

Preferred near-term path: retain the tested Flask/MySQL assessment engine; add a lightweight separately branded static tuition frontend (React/TypeScript only if justified) and authenticated API endpoints/adapters. Reuse permanent Student_ID, test IDs, assessment lifecycle, manual subjective evaluation, error taxonomy, analysis and reporting. No direct browser access to production database or secrets. No duplicate student or question-bank source of truth. Reconsider framework/database migration only as a separate decision after launch, with costs and migration risks assessed.

Student journey: parent enquiry → reviewed tuition enrolment → permanent student identity → assigned Improvia test → secure submission → objective grading + manual subjective review → error analysis → report → targeted practice → next test. Independent Improvia students follow a separate registration/acquisition path without tuition enrolment.

## 5. Fee management (tuition service)
February MVP: fee schedule per student, monthly dues, paid/unpaid/partial status, verified UPI/cash/bank entries, referral adjustments, downloadable receipt, admin reconciliation and manually initiated reminders. A screenshot or self-entered transaction ID does **not** automatically prove payment. Keep fees separate from assessment marks. Parent and student data must be access-controlled. Online gateway, automatic reconciliation and subscription billing are later options.

## 6. Referral policy — proposal, not final pricing
- ₹100 **one-time tuition credit** for both referring and new students after the new student enrolls and pays.
- Initially cap at two successful referral rewards per existing student; no cash withdrawal, no indefinite stacking; document edge cases and expiry.
- Track referring student, new student, qualifying payment, credit issue and reversals.
- Do not incentivize Google reviews.

## 7. Improvia credits — simplify
**Do not make credits a prerequisite for assigned tests or essential feedback.**
- Optional promotional **usage points**, not cash or transferable stored value.
- Future uses: extra chapter assessment, optional personalised practice, additional mock test; example costs previously explored: 30/20/60 credits, **not approved prices**.
- Potential welcome credit, tuition allowance and capped activity rewards; avoid score-based rewards, farming and complex referral-credit mechanics.
- Ledger, idempotent grant/spend, audit trail and server-side balance checks required before enabling.
- **Defer public credit wallet, buying credits and complex rewards until after the February core launch** unless capacity permits; keep the UX focused on Assigned Test, My Progress, Extra Practice.

## 8. Improvia standalone commercial validation
- Keep free diagnostic and essential feedback.
- Original hypothesis: ₹49 per additional assessment/report; **unvalidated**. Do not equate registrations with paid demand.
- Tuition cohort (10–30) tests quality; seek 50–200 **independent** users as a validation milestone, not a forecast.
- Measure test completion, report usefulness, return/reassessment rate, willingness to pay, support effort, actual gross margin, and tutor/school partnership interest.
- Human marking time is a scaling bottleneck; don't promise instant subjective results.
- At ₹49 per purchase: 100/500/1000 monthly purchases yield ₹4,900/₹24,500/₹49,000 gross before fees and costs (illustrations, not forecasts).

## 9. Marketing and acquisition
Priority: parent referrals → local organic Google Business Profile and relevant local posts → small paid Google Search test once website and timetable are ready.
- Example search terms: maths tuition Behala, Class 9 maths tuition Behala, Class 10 maths tutor Behala. Narrow radius to viable offline commute and exclude irrelevant job/online-only searches.
- Begin with **₹2,000–₹3,000 capped ad experiment**; this is a budget, not a prediction of leads. Measure qualified enquiries, demos, enrolments, cost per acquired paying student and retention. At ₹700–₹800/month, avoid high acquisition costs.
- Promote specific available batches, free demo/diagnostic and regular practice; do not promise outcomes or unbuilt features.
- Advertise Improvia independently only after product quality and retention are validated.

## 10. Timeline and acceptance gates
| Window | Priority | Exit criteria |
|---|---|---|
| Oct 26–31, 2026 | Audit repo, branches, production configuration, migrations and tests | Verified current-state checklist and stable test baseline |
| November 2026 | Stabilise question bank, taxonomy, exam submission, scoring, manual evaluation, diagnosis and report | Complete accurate end-to-end assessment-to-report test |
| December 2026 | Tuition public site, enquiry flow, resources, linked student identity and secure portal | Parent can enquire; enrolled student can reach assigned Improvia test |
| January 2027 | Fee ledger MVP, access control, pilot, backups, privacy/consent, mobile QA, marketing prep | Controlled student pilot passes; launch blockers resolved |
| February 2027 | Launch tuition website and usable Improvia MVP; enrolment/referrals; capped search ads | Real students can use system safely; metrics tracked |

If behind schedule, **ship a working public tuition site and reliable core Improvia assessment flow**; defer credits, gateway, AI marking, elaborate dashboards and automated messaging.

## 11. Cost and unit economics — planning ranges
- Self-built public site: target **₹700–₹2,000 initial** for domain/basic setup, potentially free static hosting; renewals, tax and commercial-use terms vary.
- Early advertising experiment: **₹2,000–₹3,000**, stop or revise based on measured cost per enrolment.
- Production backend/database may need paid hosting, backups and storage; do **not** promise free-tier reliability. Audit existing Render/Aiven/Cloudinary bills before budgeting.
- Tuition full occupancy: 30 × ₹700–₹800 = ₹21,000–₹24,000 monthly gross. Referral discount of ₹100 each side costs ₹200 in forgone revenue per successful pair in the affected months.
- Website and Improvia budgets should be tracked separately (domain/hosting, messaging, payment fees, support/marking, ads, refunds and tax).

## 12. UX and safety
- Student: **Assigned Test**, **My Progress**, **Extra Practice**. Teacher: **Students/Batches**, **Fees**, **Assign Tests**, **Review Progress**.
- Avoid forcing children through complicated wallets or purchasing funnels.
- Secure authentication, account ownership checks, guardian consent where applicable, least-privilege access, privacy policy, retention/deletion controls, backup/recovery, secure upload storage and audit logs before real student use.
- Preserve accurate reporting; distinguish objective auto-grading from pending human evaluation.

## 13. Open decisions and next actions
1. Confirm tuition venue, supported boards, batch composition, fee due date, session length and whether holidays affect monthly billing.
2. Inspect live repo, deployment, schema, migrations, question bank, tests and known issues; do not rewrite the stack on assumptions.
3. Define stable student identity linking independent Improvia accounts and tuition enrolments without duplicate IDs.
4. Document API contracts for assignments/results/report access and fees; keep fee records separate from learning records.
5. Decide initial authentication and guardian access policy, payment verification workflow, and worksheet copyright/permissions.
6. Establish a lightweight milestone tracker and weekly review; freeze February MVP scope.

**This document records strategic decisions and proposals from planning discussions. It does not certify implementation, market demand, pricing validity, hosting availability or security readiness.**
