# Mathematics Assessment & Improvement System — Automation Workflow Plan

## 1. Purpose

This document defines which parts of the assessment business should be manual, semi-automated, or fully automated during MVP and as the system scales.

The principle is:

> **Automate repeatable operational work; keep mathematical judgment and customer understanding human-controlled until they are proven safe to automate.**

The business should not build automation for its own sake. Every automation must reduce founder effort, improve consistency, reduce errors, or make the student experience materially better.

---

## 2. Canonical operating model

```text
Acquire
   ↓
Register / Purchase
   ↓
Create Student Record
   ↓
Create / Publish Assessment
   ↓
Student Takes Test
   ↓
Answer Submission
   ↓
Human Evaluation
   ↓
Structured Evaluation Data
   ↓
Python Analysis + Diagnosis
   ↓
Individual Report
   ↓
Email / WhatsApp Delivery
   ↓
Update Student Profile
   ↓
Recommended Focus
   ↓
Next Assessment
   ↓
Progress Measurement
```

The target operating model is:

> **The founder evaluates the student's mathematics once; the system performs the repetitive work around that evaluation.**

---

## 3. Automation levels

### Level A — Fully automatic

No routine founder action should be required after the workflow is configured.

Examples:

- Student ID creation
- Database record creation/update
- Score and percentage calculation
- Attempt-rate calculation
- Accuracy calculation
- Chapter/topic aggregation
- Error aggregation
- Longitudinal comparison
- Recurring-error detection
- Student-profile updates
- Chart generation
- PDF report generation
- Scheduled reminders
- Report email delivery

### Level B — Semi-automatic / one-click

The founder reviews or approves the action.

Examples:

- Generate a test from the question bank
- Publish/send a test
- Generate a batch of reports
- Send a WhatsApp campaign
- Review unusual/low-confidence records
- Approve a generated report
- Generate the next recommended assessment

This is the preferred operating model during early MVP testing.

### Level C — Human-controlled

Keep these human initially because quality and judgment matter more than labour savings.

- Subjective mathematics evaluation
- Ambiguous answer decisions
- Final marks awarded
- Error-code assignment when uncertain
- Question-quality decisions
- Question/marking validation
- Customer complaints and support
- Interpreting student/parent feedback

---

## 4. Workflow automation matrix

| Workflow | MVP approach | Target level | Primary tool |
|---|---|---|---|
| Acquisition | Content, search, referrals | Human | Instagram / YouTube / Google / referrals |
| Registration | Student submits form/site form | Automatic | Flask + MySQL; Forms where appropriate for admin workflows |
| Student ID | Generate permanent ID | Automatic | Application/Python + MySQL |
| Payment | Payment link/checkout | Semi-automatic initially | Payment provider |
| Registration confirmation | Confirmation message/email | Automatic | n8n + Email / WhatsApp later |
| Student database | Store/update student record | Automatic | MySQL |
| Question research | Source-grounded research | AI-assisted | NotebookLM + web |
| Question extraction | Structured extraction | Semi-automatic | Python + validation pipeline |
| Question validation | Exception review | Human exception queue | Python + admin workflow |
| Question bank | Store structured metadata | Automatic | MySQL / question-bank tools |
| Test generation | Select suitable questions | Semi-automatic | Python |
| Test PDF | Generate formatted paper | Automatic | Python + ReportLab |
| Test publishing | Publish to eligible students | Semi-automatic → automatic | Flask + n8n |
| Test reminders | Scheduled reminders | Automatic | n8n + Email / WhatsApp |
| Answer submission | Upload through exam platform | Automatic | Flask + secure storage |
| Submission organisation | Validate/store/link files | Automatic | Flask/Python + storage |
| Objective evaluation | Compare response to answer | Automatic | Application/Python |
| Subjective evaluation | Mark student's working | **Human** | Evaluator interface |
| Error coding | Dropdown/select standardized codes | Semi-automatic | Evaluation UI |
| Score calculation | Aggregate marks | Automatic | Python |
| Chapter analysis | Calculate performance | Automatic | pandas |
| Error analysis | Counts, marks lost, trends | Automatic | pandas |
| Recurring-error detection | Compare historical records | Automatic | Python |
| Diagnosis | Deterministic rules initially | Automatic, reviewable | Python |
| Student profile | Update cumulative history | Automatic | Python + MySQL |
| Report | Generate individual PDF | Automatic | Python + ReportLab |
| Report delivery | Email + secure link | Automatic | n8n + Email |
| Result notification | Short result message | Semi-automatic → automatic | n8n + WhatsApp Business API later |
| Monthly progress | Cumulative analysis/report | Automatic | Scheduled Python + n8n |
| Next-test recommendation | Rules based on profile | Automatic, reviewable | Python |
| Marketing content | Draft/repurpose content | AI-assisted | ChatGPT |
| CBSE/ICSE research | Research and source validation | AI-assisted | NotebookLM + web |
| Customer feedback | Collect and review | Semi-automatic | Forms + MySQL/Sheets |

---

## 5. What should happen automatically after evaluation

The desired high-leverage workflow is:

```text
Evaluator finishes marks + error codes
                 ↓
        Evaluation = COMPLETE
                 ↓
          Python analysis
                 ↓
       Score / chapter / error
                 ↓
     Longitudinal comparison
                 ↓
       Diagnosis + priorities
                 ↓
        Update student profile
                 ↓
         Generate report PDF
                 ↓
      Store report securely
                 ↓
       Email / WhatsApp result
                 ↓
        Recommend next focus
```

The evaluator should not manually recalculate scores, make charts, compare previous tests, build reports, or update cumulative statistics.

---

## 6. Recommended MVP technology stack

Keep the stack small:

```text
Flask application
       ↓
     MySQL
       ↓
Python / pandas
       ↓
ReportLab
       ↓
Email

n8n = orchestration/integrations

NotebookLM = internal research/content support
```

Google Forms/Sheets/Drive may still be used for low-risk administrative workflows, experiments, feedback, or temporary operational processes, but the student examination experience and core assessment data should remain in the application/MySQL architecture.

Do not introduce a workflow platform merely to replace a simple Python function.

---

## 7. n8n's role

n8n should orchestrate events and integrations rather than contain core assessment intelligence.

Good uses:

- Registration notifications
- Test-published notifications
- Scheduled reminders
- Submission-event routing
- Evaluation-complete triggers
- Calling Python analysis/report services
- Report-ready notifications
- Email/WhatsApp delivery
- Monthly scheduled reports
- Follow-up workflows

Do not put these in n8n:

- Core mathematical scoring logic
- Complex analytics
- Diagnosis rules
- Student-profile logic
- Exam timing authority
- Authentication/authorization
- Core database design
- AI grading

Python/application code remains the source of truth for assessment logic.

---

## 8. Research and question-bank tooling

NotebookLM is a supporting research tool, not a production dependency.

```text
Official/permitted sources
       ↓
   NotebookLM
       ↓
Research / classification / validation support
       ↓
Structured question data
       ↓
Question validation pipeline
       ↓
Question bank
```

For extracted PDFs/questions, the preferred design is:

```text
Extract
  ↓
Multiple validation signals
  ↓
High confidence → accept
Low confidence → exception queue
  ↓
Human review only where required
```

The question bank should remain structured and application-owned so it can later support test generation, analytics, and personalisation.

---

## 9. Evaluation automation boundary

The MVP should **not** attempt fully automatic grading of handwritten Mathematics.

Instead:

```text
AI / future automation
       ↓
Preliminary marks + error candidates + confidence
       ↓
High confidence ─────→ possible automatic acceptance later
       ↓
Low confidence
       ↓
Human verification
```

This is a future architecture, not an MVP launch requirement.

The evaluation data model should therefore preserve:

- Marks awarded
- Error code(s)
- Evaluator comment
- Evaluator identity
- Evaluation status
- Later: AI marks/candidates
- Later: AI confidence
- Later: human verification status

This keeps the system future-proof without making AI grading a dependency.

---

## 10. Scaling strategy

Manual evaluation is acceptable while validating demand.

Example:

```text
100 students × 15 minutes
= 25 evaluator hours per test
```

Therefore the scaling path should be:

```text
Manual evaluation
      ↓
Standardized evaluator UI
      ↓
Efficient error-code selection
      ↓
Trained evaluators / human review
      ↓
AI-assisted evaluation
      ↓
Confidence-based exception queue
```

The objective is not zero human involvement. The objective is to make human involvement occur where it adds the most value.

---

## 11. Automation priorities

### Priority 1 — Automate immediately

- Student records
- IDs
- Test/attempt data handling
- Objective scoring
- Score calculations
- Error aggregation
- Chapter analysis
- Longitudinal comparison
- Report generation
- Student-profile updates

### Priority 2 — Automate after the first working MVP

- Test publishing
- Reminders
- Email delivery
- File organisation
- WhatsApp notifications
- Monthly reports
- Next-test recommendations

### Priority 3 — Only after demand is validated

- Advanced workflow orchestration
- AI-assisted handwriting evaluation
- Adaptive question selection
- Advanced personalisation
- Tutor/school workflows
- Full student/parent dashboards

### Do not build early

- Mobile app
- Full SaaS platform
- Fully autonomous AI grader
- Complex ML recommendation engine
- Large subscription infrastructure
- Multi-subject platform

---

## 12. Commercial validation guardrail

Automation is not a substitute for product validation.

The first milestone remains:

> **20–30 real paying students who complete multiple assessment cycles.**

Track:

- Registration → payment
- Payment → attempt
- Attempt → report viewed
- Test 1 → Test 2 → Test 3
- Retention
- Referrals
- Student/guardian satisfaction
- Evaluation time
- Cost per student
- Willingness to pay

The most important validation question is:

> **Do students return because the diagnosis and improvement guidance are useful?**

If the answer is no, more automation or technology is not the solution.

---

## 13. Evolution of the operating model

### V1 — Founder-operated MVP

```text
Student
 → Flask/MySQL
 → Human evaluation
 → Python analysis
 → PDF report
 → Email
```

### V2 — Automated operations

```text
Student
 → Flask/MySQL
 → Evaluation
 → n8n orchestration
 → Python analysis/reporting
 → Email/WhatsApp
 → Profile update
```

### V3 — Productised analytics

```text
Student
 → Assessment
 → Evaluation
 → Longitudinal profile
 → Dashboard
 → Recommendations
```

### V4 — AI-assisted assessment

```text
Submission
 → AI preliminary evaluation
 → Confidence check
 → Human exception queue
 → Verified evaluation
 → Diagnosis
 → Personalised next assessment
```

### V5 — Scalable assessment platform

```text
Students / Tutors / Schools
          ↓
Assessment platform
          ↓
Evaluation + analytics + diagnosis
          ↓
Personalised improvement system
```

Never build V5 infrastructure simply because it is technically possible. Earn each stage through demonstrated customer value and operational need.
